"""
Basic usage example for Research Agent.

This example demonstrates how to use the ResearchAgent to discover
trending technical topics from YouTube, including macro mode for
cross-referencing with authority finance/business channels, and
multi-source trend aggregation with story pitch generation.
"""

import os
from research_agent import ResearchAgent, QuotaExceededError, NetworkError


def standard_mode_example():
    """Standard mode: discover trending technical topics."""
    print("=== Standard Mode ===\n")

    agent = ResearchAgent()

    try:
        results = agent.get_trending_topics(
            keywords=["python tutorial", "javascript", "docker", "kubernetes"],
            days_back=7,
            min_views=5000,
        )

        print(f"Found {len(results['topics'])} trending topics\n")

        for topic in results["topics"]:
            print(f"Topic: {topic['topic_name']}")
            print(f"Category: {topic['category']}")
            print(f"Trend Score: {topic['trend_score']:.2f}")
            print(f"Videos: {topic['video_count']}")
            if topic["top_videos"]:
                print(f"Top Video: {topic['top_videos'][0]['title']}")
                print(f"  Views: {topic['top_videos'][0]['view_count']:,}")
            print()

        metadata = results["metadata"]
        print(f"Total videos analyzed: {metadata['total_videos_analyzed']}")
        print(f"Average trend score: {metadata['average_trend_score']:.2f}")

    except QuotaExceededError as e:
        print(f"API quota exceeded: {e}")
        print("Try again after quota resets")

    except NetworkError as e:
        print(f"Network error: {e}")
        print("Check your internet connection")

    except Exception as e:
        print(f"Unexpected error: {e}")


def macro_mode_example():
    """Macro mode: cross-reference trends with authority channels."""
    print("\n=== Macro Mode ===\n")

    agent = ResearchAgent()

    try:
        results = agent.get_trending_topics(
            keywords=["ai", "nvidia", "cloud computing", "saas"],
            days_back=7,
            min_views=5000,
            macro_mode=True,
        )

        print(f"Found {len(results['topics'])} trending topics (macro mode)\n")

        for topic in results["topics"]:
            print(f"Topic: {topic['topic_name']}")
            print(f"Trend Score: {topic['trend_score']:.2f}")

            fc = topic.get("finance_context", {})
            if fc.get("authority_channel_match"):
                print("  ★ Matched in authority channels (2x bonus applied)")
            print(f"  Macro Relevance: {fc.get('macro_relevance_score', 0):.2f}")

            tickers = fc.get("stock_tickers", [])
            if tickers:
                print(f"  Stock Tickers: {', '.join('$' + t for t in tickers)}")

            companies = fc.get("mentioned_companies", [])
            if companies:
                print(f"  Companies: {', '.join(companies)}")

            print()

        metadata = results["metadata"]
        print(f"Macro mode enabled: {metadata.get('macro_mode_enabled', False)}")
        print(f"Authority channels checked: {metadata.get('authority_channels_checked', 0)}")

    except QuotaExceededError as e:
        print(f"API quota exceeded: {e}")
        print("Macro mode uses ~50-100 extra quota units for authority channels")

    except Exception as e:
        print(f"Unexpected error: {e}")


def multi_source_example():
    """Multi-source mode: aggregate trends from 5 data sources and generate pitches."""
    print("\n=== Multi-Source Mode ===\n")

    # Requires OPENAI_API_KEY for pitch generation
    # Data source clients (Google Trends, Reddit, Yahoo Finance, Wikipedia) need no keys
    agent = ResearchAgent()

    try:
        # Step 1: Fetch and merge trends from all 5 sources
        unified_topics = agent.get_trending_topics_multi_source()

        print(f"Discovered {len(unified_topics)} unified topics across all sources\n")

        for topic in unified_topics[:5]:  # Show top 5
            print(f"Topic: {topic.topic_name}")
            print(f"  Category: {topic.category}")
            print(f"  Trend Score: {topic.trend_score:.2f}")
            print(f"  Sources: {topic.source_count}")
            print(f"  High Confidence: {topic.high_confidence}")

            # Access source attribution
            for src in topic.sources:
                print(f"    - {src.get('source_name', 'unknown')}: {src.get('source_url', '')}")

            # Access finance context
            fc = topic.finance_context
            if fc.get("stock_tickers"):
                print(f"  Tickers: {', '.join('$' + t for t in fc['stock_tickers'])}")
            if fc.get("mentioned_companies"):
                print(f"  Companies: {', '.join(fc['mentioned_companies'])}")

            print()

        # Step 2: Generate story pitches and let the user select one
        # This calls GPT-4o-mini to synthesize trends into compelling video angles,
        # then presents a numbered list for human-in-the-loop selection.
        print("Generating story pitches from unified trends...\n")
        selected_pitch = agent.generate_and_select_pitch(unified_topics)

        print(f"\nSelected Pitch: {selected_pitch.title}")
        print(f"  Hook: {selected_pitch.hook}")
        print(f"  Context Type: {selected_pitch.context_type}")
        print(f"  Category: {selected_pitch.category}")
        print(f"  Data Note: {selected_pitch.data_note}")
        print(f"  Estimated Interest: {selected_pitch.estimated_interest:.2f}")
        print(f"  Source Trends: {len(selected_pitch.source_trends)}")

    except Exception as e:
        print(f"Error: {e}")


def main():
    # Make sure you have YOUTUBE_API_KEY in your .env file
    # For multi-source mode, also set OPENAI_API_KEY
    standard_mode_example()
    macro_mode_example()
    multi_source_example()


if __name__ == "__main__":
    main()
