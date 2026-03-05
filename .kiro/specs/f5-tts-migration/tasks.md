# Implementation Plan: F5-TTS MLX Migration

> **SUPERSEDED**: This spec was abandoned in favor of Fish Audio. The F5-TTS code has been
> removed and replaced with a Fish Audio cloud API integration. See the voice_synthesizer
> module for the current implementation.

## Status: ABANDONED

The user decided against F5-TTS MLX in favor of Fish Audio due to simpler integration
(cloud API vs local model). All F5-TTS code (F5TTSClient, PacingProcessor) has been
removed and replaced with FishAudioClient.
