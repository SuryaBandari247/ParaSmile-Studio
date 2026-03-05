# Requirements Document

## Introduction

The Keyword Suggestion Tool is a user-facing feature in the Visual Panel that helps video producers discover better stock footage keywords for each scene. Currently, keywords are either manually typed or auto-extracted via a simple GPT call in `asset_orchestrator/keyword_extractor.py`. This feature adds a per-scene "Suggest Keywords" button that triggers a context-aware keyword researcher. The researcher analyzes the current scene's narration plus the surrounding scenes' context (before and after) to produce ranked, visually specific keyword suggestions. The user can then accept, modify, or ignore the suggestions at any point in their workflow — before rendering, after rendering, or while iterating on visuals. Accepted keywords are stored back into the scene's `visual_data` for use by the clip timeline and stock footage search.

## Glossary

- **Keyword_Suggestion_Tool**: The user-facing feature comprising a frontend button, a backend API endpoint, and a context-aware keyword research engine that produces ranked keyword suggestions per scene
- **Visual_Panel**: The existing React component (`frontend/src/components/visual/VisualPanel.tsx`) that displays scene cards with clip timelines, footage search, and render controls
- **Scene_Card**: A single scene's UI card within the Visual_Panel, showing preview, narration, clip timeline, and action buttons
- **Keyword_Researcher**: The backend module that analyzes scene narration and surrounding scene context to generate ranked keyword suggestions with visual synonyms
- **Surrounding_Context**: The narration text from the scene immediately before (previous scene) and immediately after (next scene) the target scene, used to improve keyword relevance
- **Keyword_Suggestion**: A single suggested search term returned by the Keyword_Researcher, including a relevance rank and an optional visual synonym mapping
- **Suggestion_List**: The ordered list of Keyword_Suggestions returned for a single scene, ranked from most relevant to least relevant
- **Visual_Synonym**: An alternative search term that maps a niche or proprietary subject to a visually equivalent general term suitable for stock libraries (e.g., "ASML EUV" → "semiconductor cleanroom laser")
- **Aesthetic_Hint**: A style modifier (e.g., "dark lighting", "macro close-up", "slow motion") derived from the overall script tone, appended to suggestions to bias stock searches toward a consistent look
- **Blocklist**: A maintained list of banned generic/cliché keyword patterns that the Keyword_Researcher filters out (e.g., "man in office", "business meeting", "woman at computer")
- **Scene_Visual_Data**: The `visual_data` JSON field on a scene record that stores keywords, clips, and other visual metadata, as persisted via the `SceneUpdate` model

## Requirements

### Requirement 1: Per-Scene Keyword Suggestion Button

**User Story:** As a video producer, I want a "Suggest Keywords" button on each stock footage scene card in the Visual Panel, so that I can request keyword suggestions for any scene at any time.

#### Acceptance Criteria

1. THE Visual_Panel SHALL display a "Suggest Keywords" button on each Scene_Card that uses a stock footage visual type (stock_video, stock_with_text, stock_with_stat, stock_quote)
2. WHEN the user clicks the "Suggest Keywords" button, THE Visual_Panel SHALL send a request to the backend keyword suggestion API endpoint for that scene
3. WHILE the keyword suggestion request is in progress, THE Visual_Panel SHALL display a loading indicator on the Scene_Card and disable the "Suggest Keywords" button to prevent duplicate requests
4. THE "Suggest Keywords" button SHALL be available regardless of the scene's render status (PENDING, RUNNING, RENDERED, or FAILED)
5. IF the keyword suggestion request fails, THEN THE Visual_Panel SHALL display an error message on the Scene_Card and re-enable the "Suggest Keywords" button

### Requirement 2: Context-Aware Keyword Generation

**User Story:** As a video producer, I want keyword suggestions that consider the narration of surrounding scenes (before and after), so that suggestions are contextually relevant to the narrative flow.

#### Acceptance Criteria

1. WHEN generating keywords for a scene, THE Keyword_Researcher SHALL analyze the target scene's narration text as the primary input
2. WHEN the target scene has a preceding scene, THE Keyword_Researcher SHALL include the preceding scene's narration text as Surrounding_Context to inform keyword generation
3. WHEN the target scene has a following scene, THE Keyword_Researcher SHALL include the following scene's narration text as Surrounding_Context to inform keyword generation
4. WHEN the target scene is the first scene, THE Keyword_Researcher SHALL generate keywords using only the target scene narration and the following scene's context
5. WHEN the target scene is the last scene, THE Keyword_Researcher SHALL generate keywords using only the target scene narration and the preceding scene's context
6. THE Keyword_Researcher SHALL use an LLM (GPT-4o-mini) to analyze the combined narration context and produce a Suggestion_List of 5-8 ranked keyword suggestions
7. IF the LLM call fails, THEN THE Keyword_Researcher SHALL fall back to extracting concrete nouns and adjectives from the target scene's narration text

### Requirement 3: Suggestion Display and User Selection

**User Story:** As a video producer, I want to see a ranked list of suggested keywords and be able to pick, edit, or ignore them, so that I stay in control of my footage search terms.

#### Acceptance Criteria

1. WHEN keyword suggestions are returned, THE Visual_Panel SHALL display the Suggestion_List as a selectable list within the Scene_Card
2. EACH item in the Suggestion_List SHALL display the suggested keyword text and its relevance rank
3. WHEN a Keyword_Suggestion includes a Visual_Synonym mapping, THE Visual_Panel SHALL display both the original niche term and the suggested synonym (e.g., "ASML → semiconductor cleanroom")
4. THE Visual_Panel SHALL allow the user to select one or more keywords from the Suggestion_List by clicking on them
5. THE Visual_Panel SHALL allow the user to edit any suggested keyword text inline before accepting it
6. THE Visual_Panel SHALL provide an "Accept Selected" action that writes the chosen keywords into the scene's Visual_Data
7. THE Visual_Panel SHALL provide a "Dismiss" action that closes the Suggestion_List without modifying the scene
8. WHEN the user accepts keywords, THE Visual_Panel SHALL merge the accepted keywords with any existing keywords in the scene's Visual_Data, placing accepted keywords first

### Requirement 4: Backend Keyword Suggestion API Endpoint

**User Story:** As a frontend developer, I want a dedicated API endpoint for keyword suggestions, so that the Visual Panel can request suggestions per scene.

#### Acceptance Criteria

1. THE Studio_API SHALL expose a POST endpoint at `/api/projects/{project_id}/scenes/{scene_id}/suggest-keywords` that triggers keyword research for the specified scene
2. THE endpoint SHALL retrieve the target scene's narration text and the narration text of the immediately preceding and following scenes from the project's scene list
3. THE endpoint SHALL pass the narration context to the Keyword_Researcher and return the Suggestion_List as a JSON response
4. THE Suggestion_List response SHALL be a JSON array where each entry contains: keyword (string), rank (integer), original_term (string or null), and visual_synonym (string or null)
5. IF the specified scene does not exist, THEN THE endpoint SHALL return HTTP 404 with a descriptive error message
6. IF the specified scene does not use a stock footage visual type, THEN THE endpoint SHALL return HTTP 422 with a message indicating keyword suggestions are only available for stock footage scenes

### Requirement 5: Anti-Pattern Enforcement

**User Story:** As a content producer, I want the keyword researcher to reject generic or cliché stock footage keywords, so that suggestions maintain a professional, technical aesthetic.

#### Acceptance Criteria

1. THE Keyword_Researcher SHALL maintain a Blocklist of banned keyword patterns: "man in office", "woman at desk", "business meeting", "people shaking hands", "generic office", "happy team", "thumbs up", "woman at computer"
2. WHEN a generated keyword matches a Blocklist pattern, THE Keyword_Researcher SHALL replace the keyword with a more specific alternative derived from the narration context
3. THE Keyword_Researcher SHALL prefer technical, specific, and visually concrete keywords over abstract or generic ones (e.g., "circuit board macro blue LED" over "technology")
4. THE Keyword_Researcher SHALL log every Blocklist replacement with the original and replacement keyword for auditability

### Requirement 6: Visual Synonym Generation for Niche Topics

**User Story:** As a video producer covering niche technical topics, I want the researcher to generate visual synonyms for proprietary or obscure subjects, so that stock footage searches return usable results.

#### Acceptance Criteria

1. WHEN the narration references a niche or proprietary subject, THE Keyword_Researcher SHALL generate Visual_Synonyms that map the niche term to a visually equivalent general term (e.g., "ASML" → "semiconductor cleanroom", "EUV light" → "laser beam laboratory")
2. THE Keyword_Researcher SHALL include both the original niche term and the Visual_Synonym in the Suggestion_List so the user can choose which to use
3. THE Keyword_Researcher SHALL generate Visual_Synonyms by identifying terms in the narration that are unlikely to return results on general stock footage libraries

### Requirement 7: Aesthetic Consistency Hints

**User Story:** As a video producer, I want keyword suggestions to include style hints that keep the visual mood consistent across scenes, so that the final video feels cohesive.

#### Acceptance Criteria

1. THE Keyword_Researcher SHALL analyze the overall script tone (subject matter, narration style, dominant emotion) and derive 2-3 Aesthetic_Hints for the video
2. THE Aesthetic_Hints SHALL be style modifiers suitable for appending to stock footage searches (e.g., "dark lighting", "close-up macro", "slow motion", "aerial view")
3. THE Suggestion_List response SHALL include the Aesthetic_Hints as a separate field so the frontend can display them to the user
4. THE Visual_Panel SHALL display the Aesthetic_Hints alongside the Suggestion_List and allow the user to optionally append a hint to selected keywords before accepting

### Requirement 8: Accepted Keywords Persistence

**User Story:** As a video producer, I want accepted keyword suggestions to be saved into the scene's visual data, so that they are available for clip timeline searches and future renders.

#### Acceptance Criteria

1. WHEN the user accepts keywords from the Suggestion_List, THE Visual_Panel SHALL update the scene's Visual_Data keywords field via the existing PATCH `/api/projects/{project_id}/scenes/{scene_id}` endpoint
2. THE accepted keywords SHALL be stored in the scene's `visual_data.keywords` array, prepended before any previously existing keywords
3. WHEN the scene has clip timeline entries, THE Visual_Panel SHALL offer to update clip keywords with the newly accepted keywords
4. THE accepted keywords SHALL persist across page reloads by being stored in the database via the scene update API
