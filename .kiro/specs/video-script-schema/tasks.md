# Implementation Plan: Keyword Suggestion Tool

## Overview

Implement a per-scene "Suggest Keywords" feature in the Visual Panel. The backend adds a `KeywordResearcher` module and a new API endpoint; the frontend adds suggestion UI with accept/dismiss/edit flows. Implementation proceeds bottom-up: data models → backend logic → API endpoint → frontend types/client → UI components → integration wiring.

## Tasks

- [x] 1. Create KeywordResearcher module with data models and blocklist
  - [x] 1.1 Create `asset_orchestrator/keyword_researcher.py` with `KeywordSuggestion`, `SuggestionResponse` Pydantic models, `BLOCKLIST` constant, and `KeywordResearcher` class skeleton
    - Define `KeywordSuggestion(BaseModel)` with fields: `keyword: str`, `rank: int`, `original_term: str | None`, `visual_synonym: str | None`
    - Define `SuggestionResponse(BaseModel)` with fields: `suggestions: list[KeywordSuggestion]`, `aesthetic_hints: list[str]`
    - Define `BLOCKLIST` with all 8 banned patterns from requirements
    - Implement `_is_blocked(keyword)` — case-insensitive substring match against blocklist
    - Implement `_filter_blocklist(suggestions, narration)` — replace blocked keywords with context-derived alternatives, log each replacement
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 1.2 Implement `_research_with_llm` method on KeywordResearcher
    - Build structured prompt with target narration, prev/next narration context, script tone, blocklist rules, and synonym instructions
    - Call GPT-4o-mini via OpenAI client, parse JSON response into `SuggestionResponse`
    - Apply `_filter_blocklist` to LLM output
    - Generate 5-8 ranked suggestions and 2-3 aesthetic hints
    - _Requirements: 2.1, 2.2, 2.3, 2.6, 6.1, 6.2, 6.3, 7.1, 7.2_

  - [x] 1.3 Implement `_research_fallback` method on KeywordResearcher
    - Extract concrete nouns and adjectives from narration text when LLM fails
    - Return valid `SuggestionResponse` with 5-8 suggestions and 2-3 generic aesthetic hints
    - _Requirements: 2.7_

  - [x] 1.4 Implement `research()` orchestrator method on KeywordResearcher
    - Try `_research_with_llm`, catch exceptions and fall back to `_research_fallback`
    - Handle edge cases: first scene (no prev), last scene (no next), empty narration
    - _Requirements: 2.4, 2.5_

  - [ ]* 1.5 Write property test: Blocklist filtering (Property 8)
    - **Property 8: Blocklist filtering**
    - Generate random keyword lists including blocklisted terms → pass through `_filter_blocklist` → assert no output keyword matches any blocklist entry (case-insensitive substring)
    - File: `tests/property/test_keyword_researcher_properties.py`
    - **Validates: Requirements 5.2**

  - [ ]* 1.6 Write property test: Suggestion count and aesthetic hint bounds (Property 2)
    - **Property 2: Suggestion count and aesthetic hint count bounds**
    - Generate random narration strings → call `KeywordResearcher.research()` with mocked LLM → assert 5-8 suggestions with unique ranks 1..N and 2-3 aesthetic hints
    - File: `tests/property/test_keyword_researcher_properties.py`
    - **Validates: Requirements 2.6, 7.1**

  - [ ]* 1.7 Write property test: Visual synonym structural consistency (Property 9)
    - **Property 9: Visual synonym structural consistency**
    - Generate random `SuggestionResponse` objects → assert `visual_synonym` is non-null iff `original_term` is non-null
    - File: `tests/property/test_keyword_researcher_properties.py`
    - **Validates: Requirements 6.2**

  - [ ]* 1.8 Write unit tests for KeywordResearcher
    - Test blocklist catches each specific banned pattern and logs replacements
    - Test LLM fallback produces non-empty keywords from sample narration
    - Test empty narration returns valid response
    - Test prompt includes prev/next narration when provided
    - File: `tests/unit/test_keyword_researcher.py`
    - _Requirements: 2.1, 2.2, 2.3, 2.7, 5.1, 5.2, 5.4_

- [x] 2. Extend VisualService and API router with suggest-keywords endpoint
  - [x] 2.1 Add `suggest_keywords(project_id, scene_id)` method to `studio_api/services/visual_service.py`
    - Load target scene by ID, verify it exists (raise ValueError if not)
    - Verify scene `visual_type` is in `{stock_video, stock_with_text, stock_with_stat, stock_quote}` (raise ValueError if not)
    - Load all project scenes, find adjacent scenes by `scene_number` ordering
    - Extract narration from target, prev, and next scenes
    - Instantiate `KeywordResearcher` and call `research()` with narration context
    - Return `SuggestionResponse`
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_

  - [x] 2.2 Add `POST /{scene_id}/suggest-keywords` route to `studio_api/routers/visuals.py`
    - Define `SuggestKeywordsResponse` Pydantic model matching design spec
    - Wire route to `VisualService.suggest_keywords()`
    - Return 404 for missing scene, 422 for non-stock visual type
    - _Requirements: 4.1, 4.4, 4.5, 4.6_

  - [ ]* 2.3 Write property test: Neighbor narration context assembly (Property 5)
    - **Property 5: Neighbor narration context assembly**
    - Generate random lists of scenes (1-20) with random narration → for each scene index, call `suggest_keywords` → assert correct prev/next narration passed to researcher
    - File: `tests/property/test_keyword_researcher_properties.py`
    - **Validates: Requirements 4.2**

  - [ ]* 2.4 Write property test: Non-stock scene type rejection (Property 7)
    - **Property 7: Non-stock scene type rejection**
    - Generate random non-stock visual types → call suggest-keywords endpoint → assert HTTP 422
    - File: `tests/property/test_keyword_researcher_properties.py`
    - **Validates: Requirements 4.6**

  - [ ]* 2.5 Write property test: Response schema structure (Property 6)
    - **Property 6: Response schema structure**
    - Generate random `SuggestionResponse` objects → serialize to JSON → assert each entry has required fields with correct types
    - File: `tests/property/test_keyword_researcher_properties.py`
    - **Validates: Requirements 4.4, 7.3**

  - [ ]* 2.6 Write unit tests for suggest-keywords endpoint and VisualService.suggest_keywords
    - Test 404 for nonexistent scene
    - Test 422 for `data_chart` scene type
    - Test first scene passes `prev_narration=None`
    - Test last scene passes `next_narration=None`
    - File: `tests/unit/test_keyword_suggestion_api.py`
    - _Requirements: 4.2, 4.5, 4.6_

- [x] 3. Checkpoint — Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Add frontend types and API client for keyword suggestions
  - [x] 4.1 Add `KeywordSuggestion` and `SuggestKeywordsResponse` interfaces to `frontend/src/types/index.ts`
    - `KeywordSuggestion`: `keyword: string`, `rank: number`, `original_term: string | null`, `visual_synonym: string | null`
    - `SuggestKeywordsResponse`: `suggestions: KeywordSuggestion[]`, `aesthetic_hints: string[]`
    - _Requirements: 4.4_

  - [x] 4.2 Add `suggestKeywords(projectId, sceneId)` function to `frontend/src/api/visuals.ts`
    - POST to `/projects/${projectId}/scenes/${sceneId}/suggest-keywords`
    - Return typed `SuggestKeywordsResponse`
    - _Requirements: 4.1_

- [x] 5. Implement VisualPanel keyword suggestion UI
  - [x] 5.1 Add suggestion state management to `VisualPanel.tsx`
    - Add state: `suggestingScene: number | null`, `suggestions: Record<number, SuggestKeywordsResponse>`, `selectedSuggestions: Record<number, Set<number>>`, `editedKeywords: Record<string, string>`
    - Implement `handleSuggestKeywords(sceneId)` — calls API, stores response, handles loading/error
    - _Requirements: 1.2, 1.3, 1.5_

  - [x] 5.2 Add "Suggest Keywords" button to stock footage scene cards in `VisualPanel.tsx`
    - Render button only for stock visual types: `stock_video`, `stock_with_text`, `stock_with_stat`, `stock_quote`
    - Show button regardless of render status
    - Disable button and show loading indicator while request is in-flight
    - Show error message on failure, re-enable button
    - _Requirements: 1.1, 1.3, 1.4, 1.5_

  - [x] 5.3 Add suggestion list display and selection UI to `VisualPanel.tsx`
    - Render ranked suggestion list with keyword text and rank number
    - Show visual synonym mapping when present (e.g., "ASML → semiconductor cleanroom")
    - Display aesthetic hints alongside suggestions
    - Allow clicking suggestions to toggle selection
    - Allow inline editing of keyword text before acceptance
    - Allow optional appending of aesthetic hint to selected keywords
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.3, 7.4_

  - [x] 5.4 Implement "Accept Selected" and "Dismiss" actions in `VisualPanel.tsx`
    - "Accept Selected": merge accepted keywords (prepended) with existing `visual_data.keywords`, call PATCH endpoint
    - "Dismiss": close suggestion list without modifying scene data
    - _Requirements: 3.6, 3.7, 3.8, 8.1, 8.2_

  - [ ]* 5.5 Write property test: Suggest button visibility by visual type (Property 1)
    - **Property 1: Suggest button visibility by visual type and render status**
    - Generate random visual types and render statuses → assert button visibility matches stock-type membership
    - File: `frontend/tests/property/test_keyword_merge.test.ts`
    - **Validates: Requirements 1.1, 1.4**

  - [ ]* 5.6 Write property test: Keyword merge ordering on acceptance (Property 3)
    - **Property 3: Keyword merge ordering on acceptance**
    - Generate random existing keyword arrays and accepted keyword arrays → merge → assert result equals `[...accepted, ...existing]`
    - File: `frontend/tests/property/test_keyword_merge.test.ts`
    - **Validates: Requirements 3.6, 3.8, 8.2**

  - [ ]* 5.7 Write property test: Dismiss preserves scene state (Property 4)
    - **Property 4: Dismiss preserves scene state**
    - Generate random scene states → simulate dismiss → assert `visual_data` unchanged
    - File: `frontend/tests/property/test_keyword_merge.test.ts`
    - **Validates: Requirements 3.7**

  - [ ]* 5.8 Write property test: Keyword persistence round trip (Property 10)
    - **Property 10: Keyword persistence round trip**
    - Generate random keyword arrays → save via API → reload → assert first N elements match accepted keywords in order
    - File: `frontend/tests/property/test_keyword_merge.test.ts`
    - **Validates: Requirements 8.4**

  - [ ]* 5.9 Write unit tests for VisualPanel keyword suggestion UI
    - Test "Accept Selected" calls PATCH with correct payload (accepted keywords prepended)
    - Test inline edit modifies keyword text before acceptance
    - Test error state displays message and re-enables button
    - File: `frontend/tests/unit/test_keyword_suggestion_ui.test.tsx`
    - _Requirements: 3.5, 3.6, 3.8, 1.5_

- [x] 6. Final checkpoint — Full integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Add "Research Keywords" button to ScriptPanel
  - [x] 7.1 Add `enriching` and `enrichError` state to `frontend/src/components/script/ScriptPanel.tsx`
  - [x] 7.2 Add `handleEnrichKeywords` handler calling `scriptsApi.enrichKeywords()`
  - [x] 7.3 Add violet-themed "🔬 Research Keywords" button in version detail header (next to Finalize)
    - Available for both finalized and non-finalized scripts
    - Shows loading spinner while enriching, error banner on failure
    - _Requirements: opt-in keyword enrichment per user instruction_

- [x] 8. Fix orchestrator per-keyword search strategy
  - [x] 8.1 Replace broken `" ".join(keywords[:3])` with individual keyword search in `asset_orchestrator/orchestrator.py`
    - Each keyword searched individually per source, first result wins
    - Source-specific hints from keyword_research used when available
    - Multi-clip scenes spread different keywords across clips for variety

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use `hypothesis` (Python) and `fast-check` (TypeScript)
- The existing `keyword_extractor.py` is untouched — the new `keyword_researcher.py` complements it for the suggestion use case
- Accepted keywords persist via the existing `PATCH /scenes/{scene_id}` endpoint — no new persistence logic needed
