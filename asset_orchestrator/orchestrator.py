"""Asset Orchestrator — batch-processes Visual_Instructions into composed video assets."""

from __future__ import annotations

import logging
import os
import time
import traceback
from typing import Any

from asset_orchestrator.config import BatchResult, CompositionConfig, RenderConfig
from asset_orchestrator.scene_mapper import SceneMapper
from asset_orchestrator.scene_registry import SceneRegistry
from asset_orchestrator.renderer import Renderer

STOCK_SCENE_TYPES = {"stock_video", "stock_with_text", "stock_with_stat", "stock_quote", "social_card"}


class AssetOrchestrator:
    """Batch-processes Visual_Instructions into composed video assets."""

    def __init__(
        self,
        render_config: RenderConfig | None = None,
        composition_config: CompositionConfig | None = None,
        log_level: str = "INFO",
    ) -> None:
        """
        Args:
            render_config: Manim render settings. Defaults if None.
            composition_config: FFmpeg composition settings. Defaults if None.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        """
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        self._render_config = render_config or RenderConfig()
        self._composition_config = composition_config or CompositionConfig()

        self._registry = SceneRegistry()
        self._mapper = SceneMapper(self._registry)
        self._renderer = Renderer(self._render_config)

        # FFmpegWrapper may raise EnvironmentError if ffmpeg is not on PATH.
        self._ffmpeg: object | None = None
        try:
            from asset_orchestrator.ffmpeg_wrapper import FFmpegWrapper
            self._ffmpeg = FFmpegWrapper(self._composition_config)
        except EnvironmentError:
            self._logger.warning(
                "FFmpeg not found on PATH. Audio composition will be unavailable."
            )

        # Stock footage pipeline components (graceful init)
        self._pexels = None
        self._keyword_extractor = None
        self._compositor = None
        try:
            from asset_orchestrator.pexels_client import PexelsClient
            self._pexels = PexelsClient()
        except Exception as exc:
            self._logger.warning(
                "PexelsClient unavailable: %s. Stock scenes will use solid backgrounds.", exc
            )
        self._wikimedia = None
        try:
            from asset_orchestrator.wikimedia_client import WikimediaCommonsClient
            self._wikimedia = WikimediaCommonsClient()
        except Exception as exc:
            self._logger.warning("WikimediaCommonsClient unavailable: %s", exc)
        self._pixabay = None
        try:
            from asset_orchestrator.pixabay_client import PixabayClient
            self._pixabay = PixabayClient()
        except Exception as exc:
            self._logger.warning("PixabayClient unavailable: %s", exc)
        self._unsplash = None
        try:
            from asset_orchestrator.unsplash_client import UnsplashClient
            self._unsplash = UnsplashClient()
        except Exception as exc:
            self._logger.warning("UnsplashClient unavailable: %s", exc)
        try:
            from asset_orchestrator.keyword_extractor import KeywordExtractor
            self._keyword_extractor = KeywordExtractor(use_llm=True)
        except Exception:
            pass
        try:
            from asset_orchestrator.ffmpeg_compositor import FFmpegCompositor
            self._compositor = FFmpegCompositor()
        except Exception as exc:
            self._logger.warning("FFmpegCompositor unavailable: %s", exc)

    def process_instruction(
        self, instruction: dict, audio_path: str | None = None,
        narration_text: str | None = None,
    ) -> dict:
        """Process a single Visual_Instruction.

        Args:
            instruction: Visual_Instruction dict with keys type, title, data,
                and optionally style.
            audio_path: Optional audio file to compose with the rendered video.
            narration_text: Optional narration text for keyword extraction (stock scenes).

        Returns:
            ``{"status": "success", "output_path": str}`` on success, or
            ``{"status": "error", "error": str, "instruction": dict}`` on failure.
        """
        inst_type = instruction.get("type", "unknown")
        inst_title = instruction.get("title", "untitled")
        self._logger.info(
            "Received instruction: type=%s, title=%s", inst_type, inst_title
        )

        try:
            if inst_type in STOCK_SCENE_TYPES:
                return self._process_stock_instruction(
                    instruction, audio_path, narration_text
                )

            # ── Data chart pipeline (Manim — yfinance enrichment in codegen) ──
            if inst_type == "data_chart":
                # Enrich data with yfinance if needed, then route through Manim
                from asset_orchestrator.manim_codegen import _enrich_from_yahoo
                data = instruction.get("data", {})
                enriched = _enrich_from_yahoo(data)
                instruction = dict(instruction, data=enriched, type="data_chart")
                scene = self._mapper.map(instruction)

                self._logger.info("Render start (data_chart): title=%s", inst_title)
                start = time.time()

                duration = instruction.get("target_duration") or enriched.get("duration")
                if duration is None and narration_text:
                    word_count = len(narration_text.split())
                    duration = max(3.0, (word_count / 150) * 60)
                duration = duration or 8.0

                video_path = self._renderer.render(scene, instruction)
                elapsed_ms = (time.time() - start) * 1000
                self._logger.info(
                    "Data chart render complete: title=%s, chart_type=%s, %.1fs, elapsed=%.1fms",
                    inst_title, enriched.get("chart_type", "bar"), duration, elapsed_ms,
                )

                output_path = video_path
                if audio_path and self._ffmpeg:
                    output_path = self._ffmpeg.compose(audio_path, video_path)

                return {"status": "success", "output_path": output_path}

            # ── Manim pipeline (existing) ──
            scene = self._mapper.map(instruction)

            self._logger.info("Render start: type=%s, title=%s", inst_type, inst_title)
            start = time.time()
            video_path = self._renderer.render(scene, instruction)
            elapsed_ms = (time.time() - start) * 1000
            self._logger.info(
                "Render complete: type=%s, title=%s, elapsed=%.1fms",
                inst_type, inst_title, elapsed_ms,
            )

            output_path = video_path

            if audio_path is not None:
                if self._ffmpeg is None:
                    self._logger.error(
                        "Audio composition requested but FFmpeg is unavailable. "
                        "Returning rendered video without audio. instruction=%s",
                        instruction,
                    )
                else:
                    output_path = self._ffmpeg.compose(audio_path, video_path)

            return {"status": "success", "output_path": output_path}

        except Exception as exc:
            self._logger.error(
                "Error processing instruction: type=%s, title=%s, error=%s\n%s",
                inst_type, inst_title, exc, traceback.format_exc(),
            )
            self._cleanup_temp_files(instruction)
            return {
                "status": "error",
                "error": str(exc),
                "instruction": instruction,
            }

    def _process_stock_instruction(
        self,
        instruction: dict,
        audio_path: str | None = None,
        narration_text: str | None = None,
    ) -> dict:
        """Process a stock footage scene through the Pexels + FFmpeg pipeline.

        Supports variable duration, multi-clip jump cuts, social cards,
        and visual polish (vignette, color grade).
        """
        inst_type = instruction.get("type", "stock_video")
        inst_title = instruction.get("title", "untitled")
        data = instruction.get("data", {})

        start = time.time()

        # 1. Calculate duration from narration (or use explicit duration)
        duration = instruction.get("target_duration") or data.get("duration")
        if duration is None and narration_text:
            word_count = len(narration_text.split())
            duration = max(3.0, (word_count / 150) * 60)
        duration = duration or 8.0

        # 2. Get keywords + source-specific hints from keyword research
        keywords = data.get("keywords", [])
        keyword_research = data.get("keyword_research", {})
        source_hints: dict[str, list[str]] = {}  # {source: [queries]}

        if not keywords and narration_text and self._keyword_extractor:
            keywords = self._keyword_extractor.extract(narration_text, inst_title)
        if not keywords:
            keywords = [inst_title] if inst_title else ["abstract background"]

        # Build per-source query lists from keyword research data
        if keyword_research:
            suggestions = keyword_research.get("suggestions", [])
            for s in suggestions:
                hints = s.get("source_hints", {})
                for src, hint_query in (hints or {}).items():
                    source_hints.setdefault(src, []).append(hint_query)

        # Primary query: use first keyword individually (NOT joined)
        query = keywords[0] if keywords else "abstract background"

        # 3. Ensure compositor
        if self._compositor is None:
            from asset_orchestrator.ffmpeg_compositor import FFmpegCompositor
            self._compositor = FFmpegCompositor()

        # 4. Download footage — multi-clip for jump cuts if broll_density is high
        #    Source priority: explicit "source" in data > Pexels > Wikimedia > solid bg
        broll_density = data.get("broll_density", "low")
        user_clip_count = instruction.get("clip_count", 0)
        if user_clip_count and user_clip_count > 0:
            num_clips = user_clip_count
        else:
            num_clips = 3 if broll_density == "high" else 2 if duration > 6 else 1
        footage_source = data.get("source", "auto")  # "pexels", "pixabay", "wikimedia", or "auto"

        self._logger.info("Stock scene '%s': keywords=%s source=%s hints=%s (%.1fs)",
                          inst_title, keywords[:3], footage_source,
                          list(source_hints.keys()) if source_hints else "none", duration)

        video_path = None
        clip_paths: list[str] = []

        # ── User-defined clip timeline ────────────────────────────────
        user_clips = data.get("clips", [])
        clip_durations: list[float] | None = None

        if user_clips and isinstance(user_clips, list) and len(user_clips) > 0:
            self._logger.info("Stock scene '%s': using %d user-defined clips", inst_title, len(user_clips))
            clip_durations = []
            clip_speeds: list[float] = []
            for ci, clip_def in enumerate(user_clips):
                c_keywords = clip_def.get("keywords", query)
                c_duration = float(clip_def.get("duration", 4.0))
                c_source = clip_def.get("source", footage_source)
                c_selected_url = clip_def.get("selected_url", "")
                c_speed = float(clip_def.get("speed", 1.0))
                clip_durations.append(c_duration)
                clip_speeds.append(c_speed)

                downloaded = None

                # If user explicitly selected a video, download that specific one
                if c_selected_url:
                    self._logger.info("Clip %d: using user-selected URL: %s", ci, c_selected_url[:80])
                    downloaded = self._download_selected_url(c_selected_url, c_source, c_duration)

                # Fall back to search-based download
                if not downloaded:
                    if c_source == "wikimedia" and self._wikimedia:
                        img = self._wikimedia.search_and_download(c_keywords)
                        if img:
                            downloaded = self._compositor.image_to_video(img, duration=c_duration)
                    elif c_source == "unsplash" and self._unsplash:
                        img = self._unsplash.search_and_download(c_keywords)
                        if img:
                            downloaded = self._compositor.image_to_video(img, duration=c_duration)
                    elif c_source == "pixabay" and self._pixabay:
                        downloaded = self._pixabay.search_and_download(c_keywords, min_duration=2)
                    elif c_source in ("pexels", "auto") and self._pexels:
                        downloaded = self._pexels.search_and_download(c_keywords, min_duration=2)

                # Auto fallback chain
                if not downloaded and c_source == "auto":
                    if self._pixabay:
                        downloaded = self._pixabay.search_and_download(c_keywords, min_duration=2)
                    if not downloaded and self._wikimedia:
                        img = self._wikimedia.search_and_download(c_keywords)
                        if img:
                            downloaded = self._compositor.image_to_video(img, duration=c_duration)

                if downloaded:
                    clip_paths.append(downloaded)
                else:
                    self._logger.warning("Clip %d: no footage for '%s', using solid bg", ci, c_keywords)
                    clip_paths.append(self._compositor.generate_solid_background(duration=c_duration))

            # Override total duration to sum of clip durations
            # BUT if target_duration was explicitly provided (from audio), scale clips to match
            clip_total = sum(clip_durations)
            target_dur = instruction.get("target_duration")
            if target_dur and target_dur > 0 and abs(clip_total - target_dur) > 0.5:
                # Scale clip durations proportionally to match audio duration
                scale = target_dur / clip_total
                clip_durations = [d * scale for d in clip_durations]
                self._logger.info("Scaling clip durations by %.2fx to match audio (%.1fs → %.1fs)",
                                  scale, clip_total, target_dur)
                duration = target_dur
            else:
                duration = clip_total

            if len(clip_paths) > 1:
                video_path = self._compositor.concat_clips(clip_paths, duration, clip_durations=clip_durations, clip_speeds=clip_speeds)
            elif clip_paths:
                # Single clip — apply speed if not 1x
                if clip_speeds and clip_speeds[0] != 1.0:
                    single_out = self._compositor._gen_output_path("single_speed")
                    video_path = self._compositor._trim_speed_and_polish(clip_paths[0], clip_durations[0], clip_speeds[0], single_out)
                else:
                    video_path = clip_paths[0]

        # ── Auto clip download (no user clips) ────────────────────────
        #    Strategy: search each keyword individually per source, collect
        #    clips from the best-matching queries instead of joining keywords.
        if not video_path:
            # Build ordered query list: source-specific hints first, then individual keywords
            def _get_queries_for_source(src_name: str) -> list[str]:
                queries = []
                if src_name in source_hints:
                    queries.extend(source_hints[src_name])
                # Add individual keywords (not joined) as fallback queries
                for kw in keywords:
                    if kw not in queries:
                        queries.append(kw)
                return queries

            # Try Wikimedia first if explicitly requested
            if footage_source == "wikimedia" and self._wikimedia:
                for wq in _get_queries_for_source("wikimedia"):
                    self._logger.info("Stock scene '%s': searching Wikimedia for '%s'", inst_title, wq)
                    img_path = self._wikimedia.search_and_download(wq)
                    if img_path:
                        video_path = self._compositor.image_to_video(img_path, duration=duration)
                        break

            # Try Pixabay if explicitly requested
            if not video_path and footage_source == "pixabay" and self._pixabay:
                px_queries = _get_queries_for_source("pixabay")
                if num_clips > 1:
                    # Spread different keywords across clips for variety
                    for pq in px_queries:
                        clip_paths = self._pixabay.search_and_download_multiple(
                            pq, count=num_clips, min_duration=2
                        )
                        if clip_paths:
                            break
                else:
                    for pq in px_queries:
                        single = self._pixabay.search_and_download(pq, min_duration=3)
                        if single:
                            clip_paths = [single]
                            break

            # Try Pexels (default or auto)
            if not video_path and footage_source not in ("wikimedia", "pixabay") and self._pexels:
                pex_queries = _get_queries_for_source("pexels")
                if num_clips > 1:
                    # Search each keyword individually, collect one clip per keyword for variety
                    for pq in pex_queries:
                        clip_paths = self._pexels.search_and_download_multiple(
                            pq, count=num_clips, min_duration=2
                        )
                        if clip_paths:
                            break
                    # If first query didn't fill all clips, try remaining keywords
                    if len(clip_paths) < num_clips:
                        for pq in pex_queries[1:]:
                            if len(clip_paths) >= num_clips:
                                break
                            extra = self._pexels.search_and_download(pq, min_duration=2)
                            if extra and extra not in clip_paths:
                                clip_paths.append(extra)
                else:
                    for pq in pex_queries:
                        single = self._pexels.search_and_download(pq, min_duration=3)
                        if single:
                            clip_paths = [single]
                            break

            # Multi-clip jump cut base or single clip
            if not video_path and len(clip_paths) > 1:
                video_path = self._compositor.concat_clips(clip_paths, duration)
            elif not video_path and clip_paths:
                video_path = clip_paths[0]

            # Fallback chain for auto mode: try each keyword on Pixabay → Wikimedia
            if not video_path and footage_source == "auto" and self._pixabay:
                for fq in _get_queries_for_source("pixabay"):
                    self._logger.info("Pexels empty, trying Pixabay for '%s'", fq)
                    single = self._pixabay.search_and_download(fq, min_duration=3)
                    if single:
                        video_path = single
                        break

            if not video_path and footage_source == "auto" and self._wikimedia:
                for fq in _get_queries_for_source("wikimedia"):
                    self._logger.info("Pexels+Pixabay empty, trying Wikimedia for '%s'", fq)
                    img_path = self._wikimedia.search_and_download(fq)
                    if img_path:
                        video_path = self._compositor.image_to_video(img_path, duration=duration)
                        break

            if not video_path:
                self._logger.info("No footage found from any source, generating solid background")
                video_path = self._compositor.generate_solid_background(duration=duration)

        # 5. Compose overlay based on scene type
        effects = instruction.get("effects")
        show_title = instruction.get("show_title", False)

        if inst_type == "stock_with_text":
            heading = data.get("heading", "") if show_title else ""
            body = data.get("body", "") if show_title else ""
            output_path = self._compositor.compose_text_overlay(
                video_path,
                heading=heading,
                body=body,
                position=data.get("position", "center"),
                duration=duration,
                effects=effects,
            )
        elif inst_type == "stock_with_stat":
            if show_title:
                output_path = self._compositor.compose_stat_overlay(
                    video_path,
                    value=str(data.get("value", "")),
                    label=data.get("label", ""),
                    subtitle=data.get("subtitle", ""),
                    duration=duration,
                    effects=effects,
                )
            else:
                output_path = self._compositor.compose_text_overlay(
                    video_path, heading="", duration=duration, effects=effects,
                )
        elif inst_type == "stock_quote":
            if show_title:
                output_path = self._compositor.compose_quote_overlay(
                    video_path,
                    quote=data.get("quote", ""),
                    attribution=data.get("attribution", ""),
                    duration=duration,
                    effects=effects,
                )
            else:
                output_path = self._compositor.compose_text_overlay(
                    video_path, heading="", duration=duration, effects=effects,
                )
        elif inst_type == "social_card":
            if show_title:
                output_path = self._compositor.compose_social_card(
                    video_path,
                    platform=data.get("platform", "reddit"),
                    username=data.get("username", "u/anonymous"),
                    post_title=data.get("post_title", ""),
                    body=data.get("body", ""),
                    upvotes=data.get("upvotes", 0),
                    comments=data.get("comments", 0),
                    subreddit=data.get("subreddit", ""),
                    duration=duration,
                    effects=effects,
                )
            else:
                output_path = self._compositor.compose_text_overlay(
                    video_path, heading="", duration=duration, effects=effects,
                )
        else:
            # stock_video — title overlay only if show_title is on
            heading = data.get("title", inst_title) if show_title else ""
            output_path = self._compositor.compose_text_overlay(
                video_path,
                heading=heading,
                duration=duration,
                effects=effects,
            )

        # 6. Optionally compose with narration audio
        if audio_path and self._ffmpeg:
            output_path = self._ffmpeg.compose(audio_path, output_path)

        elapsed_ms = (time.time() - start) * 1000
        self._logger.info(
            "Stock scene complete: type=%s, title=%s, %.1fs, elapsed=%.1fms",
            inst_type, inst_title, duration, elapsed_ms,
        )

        result: dict[str, Any] = {"status": "success", "output_path": output_path}

        # Store the clips that were actually used so the UI can show them
        if user_clips and isinstance(user_clips, list) and len(user_clips) > 0:
            result["clips_used"] = user_clips
        elif clip_paths:
            per_clip_dur = round(duration / max(len(clip_paths), 1), 1)
            result["clips_used"] = [
                {"keywords": query, "duration": per_clip_dur, "source": footage_source}
                for _ in clip_paths
            ]

        return result



    def process_batch(
        self,
        instructions: list[dict],
        audio_paths: list[str] | None = None,
        narration_texts: list[str] | None = None,
    ) -> BatchResult:
        """Process a batch of Visual_Instructions.

        Continues on per-item failure — a single bad instruction never blocks
        the rest of the batch.

        Args:
            instructions: List of Visual_Instruction dicts.
            audio_paths: Optional parallel list of audio file paths.
            narration_texts: Optional parallel list of narration texts
                (used for keyword extraction in stock scenes).

        Returns:
            A :class:`BatchResult` with total, succeeded, failed, and
            per-instruction results.
        """
        results: list[dict] = []
        succeeded = 0
        failed = 0

        for i, instruction in enumerate(instructions):
            audio_path = None
            if audio_paths is not None and i < len(audio_paths):
                audio_path = audio_paths[i]

            narration_text = None
            if narration_texts is not None and i < len(narration_texts):
                narration_text = narration_texts[i]

            result = self.process_instruction(instruction, audio_path, narration_text)
            results.append(result)

            if result["status"] == "success":
                succeeded += 1
            else:
                failed += 1

        return BatchResult(
            total=len(instructions),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    def _cleanup_temp_files(self, instruction: dict) -> None:
        """Best-effort cleanup of temp files from a failed render."""
        try:
            sanitized = self._renderer.sanitize_filename(
                instruction.get("title", "untitled")
            )
            inst_type = instruction.get("type", "scene")
            output_format = self._render_config.output_format
            expected = f"{inst_type}_{sanitized}.{output_format}"
            output_dir = os.path.abspath(self._render_config.output_dir)

            # Walk the output dir looking for the partial file
            for dirpath, _, filenames in os.walk(output_dir):
                if expected in filenames:
                    path = os.path.join(dirpath, expected)
                    os.unlink(path)
                    self._logger.info("Cleaned up temp file: %s", path)
        except Exception:
            # Cleanup is best-effort; don't mask the original error
            pass
    def _download_selected_url(self, url: str, source: str, duration: float) -> str | None:
        """Download a specific video/image that the user selected from search results."""
        import hashlib
        try:
            if not url.startswith("http"):
                return None

            cache_dir = "output/stock_cache"
            os.makedirs(cache_dir, exist_ok=True)
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            if source in ("wikimedia", "unsplash"):
                # Wikimedia/Unsplash URLs are images — download and convert to video
                ext = url.rsplit(".", 1)[-1].lower() if "." in url else "jpg"
                if ext not in ("jpg", "jpeg", "png", "gif", "svg", "webp"):
                    ext = "jpg"
                filename = f"selected_{url_hash}.{ext}"
                filepath = os.path.join(cache_dir, filename)
                if not os.path.isfile(filepath):
                    self._logger.info("Downloading selected image: %s", url[:80])
                    import requests
                    resp = requests.get(url, stream=True, timeout=30)
                    resp.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=64 * 1024):
                            f.write(chunk)
                if self._compositor:
                    return self._compositor.image_to_video(os.path.abspath(filepath), duration=duration)
                return None

            # For Pexels/Pixabay, the URL is a direct video file link
            filename = f"selected_{url_hash}.mp4"
            filepath = os.path.join(cache_dir, filename)

            if os.path.isfile(filepath):
                self._logger.info("Selected video cache hit: %s", filepath)
                return os.path.abspath(filepath)

            self._logger.info("Downloading selected video: %s", url[:80])
            import requests
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    f.write(chunk)
            return os.path.abspath(filepath)
        except Exception as exc:
            self._logger.warning("Failed to download selected URL %s: %s", url[:60], exc)
            return None
