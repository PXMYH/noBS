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

    # Output
    OUTPUT_FILENAME = os.getenv('OUTPUT_FILENAME', 'index.html')

    # Server
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', '5000'))
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # HTML2Text
    HTML2TEXT_IGNORE_LINKS = True
