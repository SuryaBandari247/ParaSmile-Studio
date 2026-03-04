#!/usr/bin/env python3
"""
Generate trending_topics.json from all 5 data sources.

Fetches from Google Trends, Reddit, Yahoo Finance, Wikipedia, and YouTube,
merges/deduplicates, scores, and saves the unified result.
"""

import json
from research_agent import ResearchAgent


def main():
    print("=" * 70)
    print("Generating trending_topics.json (multi-source)")
    print("=" * 70)
    print()

    agent = ResearchAgent()
    print("✓ Agent initialized")
    print()

    print("Fetching from 5 sources: Google Trends, Reddit, Yahoo Finance, Wikipedia, YouTube...")
    print()

    detailed = agent.get_trending_topics_multi_source_detailed()
    unified = detailed["unified"]

    # Source counts
    print(f"  Google Trends: {len(detailed['google_trends'])} trends")
    print(f"  Reddit:        {len(detailed['reddit'])} posts")
    yahoo = detailed["yahoo_finance"]
    yahoo_count = sum(len(v) for v in yahoo.values() if isinstance(v, list))
    print(f"  Yahoo Finance: {yahoo_count} movers")
    print(f"  Wikipedia:     {len(detailed['wikipedia'])} events")
    print(f"  YouTube:       {len(detailed['youtube'])} topics")
    print()

    print(f"✓ Unified: {len(unified)} topics after merge + dedup")
    print()

    # Top 15
    print("Top 15 Trending Topics:")
    print("-" * 70)
    for i, topic in enumerate(unified[:15], 1):
        hc = " 🔥" if topic.get("high_confidence") else ""
        src_count = topic.get("source_count", 1)
        sources = [s.get("source_name", "") for s in topic.get("sources", [])]
        print(f"{i}. {topic['topic_name']}{hc}")
        print(f"   Score: {topic.get('trend_score', 0):.1f} | Sources: {src_count} ({', '.join(sources)})")
        print(f"   Category: {topic.get('category', '—')}")
        tickers = topic.get("finance_context", {}).get("stock_tickers", [])
        if tickers:
            print(f"   Tickers: {', '.join('$' + t for t in tickers)}")
        print()

    # Save
    output = {"topics": unified, "sources": {
        "google_trends_count": len(detailed["google_trends"]),
        "reddit_count": len(detailed["reddit"]),
        "yahoo_finance_count": yahoo_count,
        "wikipedia_count": len(detailed["wikipedia"]),
        "youtube_count": len(detailed["youtube"]),
    }}
    with open("trending_topics.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("=" * 70)
    print("✓ Saved to trending_topics.json")
    print("=" * 70)

    # Category breakdown
    categories: dict[str, int] = {}
    for t in unified:
        cat = t.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    print("\nCategory Breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    high_conf = sum(1 for t in unified if t.get("high_confidence"))
    print(f"\nHigh-confidence topics (3+ sources): {high_conf}/{len(unified)}")
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
