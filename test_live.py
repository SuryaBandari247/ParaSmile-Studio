#!/usr/bin/env python3
"""
Quick test script for Research Agent.
Run this to verify the agent works with real YouTube API.
"""

from research_agent import ResearchAgent, QuotaExceededError, NetworkError

def main():
    print("=" * 60)
    print("Research Agent - Live Test")
    print("=" * 60)
    print()
    
    try:
        # Initialize the agent
        print("Initializing Research Agent...")
        agent = ResearchAgent()
        print("✓ Agent initialized successfully")
        print()
        
        # Get trending topics
        print("Fetching trending topics (this may take 10-30 seconds)...")
        print("Keywords: python, javascript, docker")
        print("Time range: Last 7 days")
        print("Min views: 5000")
        print()
        
        results = agent.get_trending_topics(
            keywords=["python", "javascript", "docker"],
            days_back=7,
            min_views=5000
        )
        
        # Display results
        print("=" * 60)
        print(f"Found {len(results['topics'])} trending topics")
        print("=" * 60)
        print()
        
        for i, topic in enumerate(results['topics'][:5], 1):  # Show top 5
            print(f"{i}. {topic['topic_name']}")
            print(f"   Category: {topic['category']}")
            print(f"   Trend Score: {topic['trend_score']:.2f}")
            print(f"   Videos: {topic['video_count']}")
            
            if topic['top_videos']:
                top_video = topic['top_videos'][0]
                print(f"   Top Video: {top_video['title']}")
                print(f"   Views: {top_video['view_count']:,}")
                print(f"   Channel: {top_video['channel']}")
            print()
        
        # Display metadata
        print("=" * 60)
        print("Metadata")
        print("=" * 60)
        metadata = results['metadata']
        print(f"Total videos analyzed: {metadata['total_videos_analyzed']}")
        print(f"Average trend score: {metadata['average_trend_score']:.2f}")
        print(f"Query date: {metadata['query_date']}")
        print()
        
        print("✓ Test completed successfully!")
        
    except QuotaExceededError as e:
        print(f"✗ API quota exceeded: {e}")
        print("The YouTube API has a daily quota limit.")
        print("Try again tomorrow or use a different API key.")
        
    except NetworkError as e:
        print(f"✗ Network error: {e}")
        print("Check your internet connection and try again.")
        
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
