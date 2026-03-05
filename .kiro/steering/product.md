# Product: Calm Capitalist

## Objective
Automate the production of high-RPM technical finance videos (1080p, 30fps) for calmcapitalist.com using data-driven research and code-based animations.

## Anti-Patterns (NEVER DO THIS)
- Do NOT use generic AI-generated stock footage (e.g., "man in office").
- Do NOT use "yelling" or "clickbait" AI voices.
- Avoid generic transitions; prefer technical overlays.
- Do NOT render static charts — animate the investigative process.

## Engineering Standards
- All visuals must be code-generated (Manim/D3.js) or actual screen recordings.
- Scripts must be grounded in real-time data scraped from APIs (YouTube/Reddit/Yahoo Finance).
- Use Fish Speech (local) as the default TTS backend for zero-cost voice synthesis. Fish Audio cloud API and ElevenLabs are available as optional backends.

## Animation Standards (Manim)
- Use `MovingCameraScene` for camera tracking on timeseries/line charts — follow the line as it draws.
- Use `Indicate()` to highlight specific data points when the narration references them.
- Use `VGroup` to bundle related elements (e.g., company revenue + competitor growth) for fluid group transitions.
- Animate the discovery process, not just the final state — build up charts progressively.
- End-of-line value badges on timeseries, event markers for key dates.

## Target Platform
- Channel: calmcapitalist.com (YouTube + website)
- Tone: Calm, analytical, dry wit — not hype. Think Jeremy Clarkson meets Bloomberg.
- M4 48GB optimized: background renders, parallel TTS synthesis.
