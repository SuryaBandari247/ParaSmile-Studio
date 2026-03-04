"""Search panel — Step 1 of the pipeline.

Triggers the Research Agent multi-source fetch and displays results
in per-source tabs plus an Aggregated tab with the unified topics.
"""

import logging

import streamlit as st

from pipeline_ui.navigation import PipelineStep
from pipeline_ui.session_state import get_pipeline
from research_agent.agent import ResearchAgent
from research_agent.exceptions import (
    AuthenticationError,
    NetworkError,
    QuotaExceededError,
)

logger = logging.getLogger("pipeline_ui")


def render_search_panel() -> None:
    """Step 1: Trigger research and display per-source + aggregated results."""
    pipeline = get_pipeline()

    st.subheader("Trend Research")

    if st.button("Search for Trends", key="search_trends"):
        _run_search(pipeline)

    if pipeline.search_results:
        _render_tabbed_results(pipeline.search_results)

        if st.button("Regenerate", key="regenerate_pitches"):
            _run_search(pipeline)


def _run_search(pipeline) -> None:
    """Invoke ResearchAgent.get_trending_topics_multi_source_detailed."""
    with st.spinner("Fetching trends from 5 sources…"):
        try:
            agent = ResearchAgent()
            detailed = agent.get_trending_topics_multi_source_detailed()

            # Store the full detailed result (per-source + unified)
            pipeline.search_results = detailed
            pipeline.max_completed_step = max(
                pipeline.max_completed_step, int(PipelineStep.SEARCH)
            )

            total = len(detailed.get("unified", []))
            st.success(f"Found {total} unified topics across all sources")

            # Auto-save
            try:
                from content_store import ContentStore
                with ContentStore() as store:
                    store.save_search_session({"topics": detailed["unified"]})
            except Exception as exc:
                logger.warning("[Search] Auto-save failed: %s", exc)

        except QuotaExceededError as exc:
            st.error(f"API quota exceeded. Resets at {exc.reset_at.isoformat()}.")
        except NetworkError as exc:
            st.error(f"Network error: {exc}")
        except AuthenticationError as exc:
            st.error(f"Authentication error: {exc}")
            st.info("Check YOUTUBE_API_KEY in `.env`.")
        except Exception as exc:
            logger.error("[Search] %s", exc)
            st.error(f"Research failed: {exc}")


def _render_tabbed_results(results: dict) -> None:
    """Render results in tabs: one per source + Aggregated."""
    tab_names = [
        "🔗 Aggregated",
        "📈 Google Trends",
        "💬 Reddit",
        "💰 Yahoo Finance",
        "📖 Wikipedia",
        "▶️ YouTube",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_aggregated(results.get("unified", results.get("topics", [])))

    with tabs[1]:
        _render_google_trends(results.get("google_trends", []))

    with tabs[2]:
        _render_reddit(results.get("reddit", []))

    with tabs[3]:
        _render_yahoo_finance(results.get("yahoo_finance", {}))

    with tabs[4]:
        _render_wikipedia(results.get("wikipedia", []))

    with tabs[5]:
        _render_youtube(results.get("youtube", []))


# ── Aggregated ─────────────────────────────────────────────────────────────

def _render_aggregated(topics: list) -> None:
    if not topics:
        st.info("No unified topics yet.")
        return

    pipeline = get_pipeline()
    st.caption(f"{len(topics)} topics (sorted by trend score) — click Select to pick one")

    for idx, topic in enumerate(topics):
        title = topic.get("topic_name", "Untitled")
        score = topic.get("trend_score", 0)
        src_count = topic.get("source_count", 1)
        high_conf = topic.get("high_confidence", False)
        category = topic.get("category", "—")
        sources = topic.get("sources", [])
        finance = topic.get("finance_context", {})

        badge = " 🔥" if high_conf else ""
        with st.expander(f"{idx + 1}. {title}{badge}  —  score {score:.1f}", expanded=(idx < 3)):
            cols = st.columns(4)
            cols[0].metric("Category", category)
            cols[1].metric("Score", f"{score:.1f}")
            cols[2].metric("Sources", str(src_count))
            source_names = ", ".join(s.get("source_name", "") for s in sources[:5])
            cols[3].metric("From", source_names or "—")

            tickers = finance.get("stock_tickers", [])
            if tickers:
                st.caption(f"Tickers: {', '.join(tickers[:6])}")

            if st.button(f"Select this topic", key=f"select_topic_{idx}"):
                pipeline.selected_topic = topic
                pipeline.max_completed_step = max(
                    pipeline.max_completed_step, int(PipelineStep.SELECT_TOPIC)
                )
                from pipeline_ui.navigation import go_to_step
                go_to_step(PipelineStep.SCRIPT_INPUT, pipeline)
                st.rerun()


# ── Google Trends ──────────────────────────────────────────────────────────

def _render_google_trends(trends: list) -> None:
    if not trends:
        st.info(
            "No Google Trends data. The RSS feed may be temporarily "
            "unavailable. Try again in a few minutes."
        )
        return

    sorted_trends = sorted(trends, key=lambda t: t.get("approximate_search_volume", 0), reverse=True)
    st.caption(f"{len(sorted_trends)} trending searches (by search volume)")
    for t in sorted_trends:
        title = t.get("topic_name", "—")
        volume = t.get("approximate_search_volume", 0)
        related = t.get("related_queries", [])
        line = f"- **{title}**"
        if volume:
            line += f"  ({volume:,} searches)"
        if related:
            line += f"  · related: {', '.join(related[:3])}"
        st.markdown(line)


# ── Reddit ─────────────────────────────────────────────────────────────────

def _render_reddit(posts: list) -> None:
    if not posts:
        st.info("No Reddit data.")
        return

    sorted_posts = sorted(posts, key=lambda p: p.get("score", 0), reverse=True)
    st.caption(f"{len(sorted_posts)} hot posts (by upvotes)")
    for p in sorted_posts:
        title = p.get("title", "—")
        sub = p.get("subreddit", "")
        score = p.get("score", 0)
        url = p.get("url", "")
        line = f"- **{title}**"
        if sub:
            line += f"  · r/{sub}"
        if score:
            line += f"  · ⬆ {score}"
        st.markdown(line)


# ── Yahoo Finance ──────────────────────────────────────────────────────────

def _render_yahoo_finance(data: dict) -> None:
    if not data:
        st.info("No Yahoo Finance data.")
        return

    for section_key in ("gainers", "losers", "most_active", "trending_tickers"):
        items = data.get(section_key, [])
        if not items:
            continue
        # Sort by absolute change percentage
        sorted_items = sorted(
            items,
            key=lambda x: abs(x.get("regularMarketChangePercent", 0) or x.get("change_pct", 0) or 0),
            reverse=True,
        )
        label = section_key.replace("_", " ").title()
        st.markdown(f"**{label}** ({len(sorted_items)})")
        for item in sorted_items[:10]:
            symbol = item.get("symbol", "—")
            name = item.get("name") or item.get("shortName", "")
            change = item.get("regularMarketChangePercent") or item.get("change_pct", "")
            change_str = f"  ({change:+.1f}%)" if isinstance(change, (int, float)) else ""
            st.markdown(f"- `{symbol}` {name}{change_str}")


# ── Wikipedia ──────────────────────────────────────────────────────────────

def _render_wikipedia(events: list) -> None:
    if not events:
        st.info("No Wikipedia events data.")
        return

    st.caption(f"{len(events)} current events")
    for e in events:
        headline = e.get("headline", "")
        category = e.get("category", "")
        summary = e.get("summary", "")
        date = e.get("date", "")
        entities = e.get("named_entities", [])

        title_line = headline or "Untitled event"
        if category:
            title_line += f"  · {category}"
        st.markdown(f"- **{title_line}**")
        if summary:
            st.caption(summary[:250])
        if entities:
            st.caption(f"Entities: {', '.join(entities[:6])}")
        if date:
            st.caption(f"Date: {date}")


# ── YouTube ────────────────────────────────────────────────────────────────

def _render_youtube(topics: list) -> None:
    if not topics:
        st.info("No YouTube data.")
        return

    sorted_topics = sorted(topics, key=lambda t: t.get("trend_score", 0), reverse=True)
    st.caption(f"{len(sorted_topics)} trending topics from YouTube (by trend score)")
    for t in sorted_topics:
        title = t.get("topic_name", "—")
        score = t.get("trend_score", 0)
        vcount = t.get("video_count", 0)
        st.markdown(f"- **{title}** — score {score:.1f}, {vcount} videos")
