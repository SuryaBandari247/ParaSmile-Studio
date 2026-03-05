# Implementation Plan: Stock Footage Visuals

## Overview

Extend the Asset Orchestrator with stock footage support from Pexels API + FFmpeg text overlays. This is additive — no breaking changes to the existing Manim pipeline. After implementation, the Moronic Monday script can be re-rendered with real stock footage backgrounds.

## Tasks

- [x] 1. Add Pexels API key to configuration
  - [x] 1.1 Add `PEXELS_API_KEY` to `.env.example` with placeholder
  - [x] 1.2 Add `PEXELS_API_KEY` to `.env` (user must supply their own key from pexels.com)
  - [x] 1.3 Add `ConfigurationError` exception to `asset_orchestrator/exceptions.py`
  - [x] 1.4 Add `StockFootageError` exception to `asset_orchestrator/exceptions.py`
  - [x] 1.5 Add `requests` to `requirements.txt` if not already present
    - _Requirements: R1.1, R1.6_

- [x] 2. Implement PexelsClient
  - [x] 2.1 Create `asset_orchestrator/pexels_client.py`
    - _Requirements: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6, R1.7, R1.8, R1.9_

  - [x] 2.2 Write unit tests for PexelsClient (`tests/unit/test_pexels_client.py`)
    - _Requirements: R1.1–R1.9_

- [x] 3. Implement KeywordExtractor
  - [x] 3.1 Create `asset_orchestrator/keyword_extractor.py`
    - _Requirements: R2.1, R2.2, R2.3, R2.4, R2.5_

  - [x] 3.2 Write unit tests for KeywordExtractor (`tests/unit/test_keyword_extractor.py`)
    - _Requirements: R2.1–R2.5_

- [x] 4. Implement FFmpegCompositor
  - [x] 4.1 Create `asset_orchestrator/ffmpeg_compositor.py`
    - _Requirements: R3.1, R3.2, R3.3, R3.4, R3.5, R3.6, R3.7, R3.8_

  - [x] 4.2 Write unit tests for FFmpegCompositor (`tests/unit/test_ffmpeg_compositor.py`)
    - _Requirements: R3.1–R3.8_

- [x] 5. Implement Stock Scene Types and Registry
  - [x] 5.1 Create `asset_orchestrator/stock_scenes.py`
    - _Requirements: R4.1, R4.2, R4.3, R4.4_

  - [x] 5.2 Register stock scene types in SceneRegistry
    - _Requirements: R4.6_

  - [x] 5.3 Write unit tests for stock scenes (`tests/unit/test_stock_scenes.py`)
    - _Requirements: R4.1–R4.6_

- [x] 6. Integrate Stock Pipeline into Orchestrator
  - [x] 6.1 Extend `AssetOrchestrator.__init__` to initialize PexelsClient, KeywordExtractor, and FFmpegCompositor
    - _Requirements: R5.1_

  - [x] 6.2 Add `_process_stock_instruction()` method to AssetOrchestrator
    - _Requirements: R5.2, R5.3_

  - [x] 6.3 Modify `process_instruction()` to route stock scene types
    - _Requirements: R5.1, R5.5_

  - [x] 6.4 Write unit tests for orchestrator stock integration (`tests/unit/test_orchestrator_stock.py`)
    - _Requirements: R5.1–R5.5_

- [x] 7. Update Video Script JSON and Re-render Moronic Monday
  - [x] 7.1 Rewrite `output/moronic_monday_video_script.json` to use stock scene types
    - _Requirements: R6.1–R6.5_

  - [x] 7.2 Update `render_moronic_monday.py` to work with the extended orchestrator
    - _Requirements: R5.2_

  - [x] 7.3 Add `PEXELS_API_KEY` to `.env.example` documentation
    - _Requirements: R1.1_

- [x] 8. Final checkpoint — Run all tests
  - 481 tests passing (up from 425), no regressions
  - Stock + Manim scenes coexist in the same batch

## Notes

- User must obtain a free Pexels API key from https://www.pexels.com/api/
- Pexels free tier: 200 requests/hour, no watermarks, free for commercial use
- The solid-color fallback ensures the pipeline never fails just because stock footage is unavailable
- Existing tests continue passing — this is purely additive
- Manim scenes remain unchanged
