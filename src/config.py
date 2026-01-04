import os


class Config:
    """Configuration class for NoBS News Aggregator."""

    # RSS Feeds
    RSS_FEED_URLS = [
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
        "https://www.theguardian.com/us/business/rss",
        "http://feeds.washingtonpost.com/rss/business?itid=lk_inline_manual_37"
    ]

    # Timezone
    TIMEZONE = os.getenv('TIMEZONE', 'US/Central')

    # Archive service
    ARCHIVE_SERVICE_URL = os.getenv('ARCHIVE_SERVICE_URL', 'https://archive.ph/submit/?url=')

    # Output (write to data directory for simple text-based storage)
    # Use absolute path relative to the config file location for reliability
    _config_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_config_dir)
    OUTPUT_FILENAME = os.getenv('OUTPUT_FILENAME', os.path.join(_project_root, 'data', 'news_source.txt'))

    # Server
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', '5000'))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # HTML2Text
    HTML2TEXT_IGNORE_LINKS = True

    # LLM Configuration for Summarization
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    LLM_MODEL = os.getenv('LLM_MODEL', 'openrouter/anthropic/claude-3.5-sonnet')
    GENERATE_DIGEST = os.getenv('GENERATE_DIGEST', 'false').lower() == 'true'
    MAX_ARTICLES_PER_CATEGORY = int(os.getenv('MAX_ARTICLES_PER_CATEGORY', '50'))
