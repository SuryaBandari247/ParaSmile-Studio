# ParaSmile Studio

Python-based YouTube Data API scraper for discovering trending technical topics. Part of ParaSmile Studio.

## Setup

### Prerequisites

- Python 3.13+
- YouTube Data API key ([Get one here](https://console.cloud.google.com/apis/credentials))

### Installation

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
```

## Usage

### Basic Example

```python
from research_agent import ResearchAgent, QuotaExceededError, NetworkError

# Initialize agent
agent = ResearchAgent()

try:
    # Get trending topics
    results = agent.get_trending_topics(
        keywords=["python tutorial", "devops automation"],
        days_back=7,
        min_views=1000
    )
    
    # Access results
    for topic in results['topics']:
        print(f"{topic['topic_name']}: {topic['trend_score']:.2f}")
        print(f"  Category: {topic['category']}")
        print(f"  Videos: {topic['video_count']}")
        
except QuotaExceededError:
    print("API quota exceeded - try again later")
except NetworkError:
    print("Network error - check connection")
```

### Macro Mode

Macro mode cross-references your technical trends with authority finance/business channels to surface topics with broader market relevance. When enabled, topics that appear in authority channel content receive a 2x trend score bonus and include financial context.

**Authority channels checked:** The Economist, Bloomberg Technology, CNBC Television, Financial Times, Wall Street Journal, TechCrunch, The Verge.

```python
from research_agent import ResearchAgent

agent = ResearchAgent()

results = agent.get_trending_topics(
    keywords=["ai", "nvidia", "cloud computing"],
    days_back=7,
    min_views=5000,
    macro_mode=True,
)

for topic in results["topics"]:
    fc = topic["finance_context"]
    print(f"{topic['topic_name']} (score: {topic['trend_score']:.0f})")

    if fc["authority_channel_match"]:
        print("  ★ Authority channel match — 2x bonus applied")

    if fc["stock_tickers"]:
        print(f"  Tickers: {', '.join('$' + t for t in fc['stock_tickers'])}")

    if fc["mentioned_companies"]:
        print(f"  Companies: {', '.join(fc['mentioned_companies'])}")

    print(f"  Macro relevance: {fc['macro_relevance_score']:.2f}")
```

**`finance_context` structure** (present on every topic, empty in standard mode):

| Field | Type | Description |
|---|---|---|
| `stock_tickers` | `list[str]` | Extracted ticker symbols, e.g. `["NVDA", "AMZN"]` |
| `mentioned_companies` | `list[str]` | Company names found in metadata |
| `macro_relevance_score` | `float` | 0–1 score based on authority channel presence |
| `authority_channel_match` | `bool` | Whether the topic appeared in authority content |

Macro mode adds ~50–100 extra API quota units per query (7 channels × 5 videos + detail fetches).

See `examples/basic_usage.py` for a complete example including both standard and macro mode.

### CLI Usage

Generate trending topics from the command line:

```bash
# Standard mode
python generate_trending_topics.py

# Macro mode — cross-reference with authority channels
python generate_trending_topics.py --macro-mode
```

## Testing

Run all tests:
```bash
source venv/bin/activate
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=research_agent --cov-report=html
```

## Project Structure

```
research_agent/
├── __init__.py           # Package initialization
├── agent.py              # Main ResearchAgent interface
├── api_client.py         # YouTube API client
├── rate_limiter.py       # API quota management
├── analyzer.py           # Trend analysis
├── cross_reference.py    # Authority channel cross-referencing & finance context
├── cache.py              # Topic caching
├── config.py             # Configuration management
├── logger.py             # Logging setup
├── models.py             # Data models (incl. FinanceContext)
└── exceptions.py         # Custom exceptions
```

## Configuration

### Default Configuration

- Daily quota limit: 10,000 units
- Cache TTL: 6 hours
- Minimum trend score: 30
- Minimum view count: 1,000
- Search window: 7 days
- Max videos per query: 50

### Custom Configuration

Create a config file (YAML or JSON):

```yaml
# config.yaml
youtube_api_key: "your-api-key"
daily_quota_limit: 10000
cache_ttl_hours: 6
min_trend_score: 30
max_videos_per_query: 50
default_keywords:
  - "python tutorial"
  - "javascript"
  - "docker"
log_level: "INFO"
structured_logging: false

# Macro mode settings
macro_mode_enabled: false
max_videos_per_authority_channel: 5
topic_similarity_threshold: 0.3
macro_bonus_multiplier: 2.0
```

Load custom config:

```python
agent = ResearchAgent(config={"config_file": "config.yaml"})
```

Or pass config directly:

```python
config = {
    "daily_quota_limit": 5000,
    "cache_ttl_hours": 12,
    "min_trend_score": 40
}
agent = ResearchAgent(config=config)
```

## API Quota Management

The YouTube Data API has a daily quota of 10,000 units:
- Search operations: 100 units
- Video details: 1 unit per video

The rate limiter:
- Logs warnings at 80% usage
- Blocks calls at 95% usage (circuit breaker)
- Persists state across restarts

## License

Proprietary - ParaSmile Studio
