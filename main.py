from flask import Flask, render_template
import feedparser
import concurrent.futures
import logging
import pytz
from datetime import datetime

app = Flask(__name__)

# Configure Flask's logger
app.logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Define a list of RSS feed URLs
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


def fetch_feed_data(url):
    feed = feedparser.parse(url)
    feed_title = feed.feed.title
    articles = feed.entries
    return {"feed_title": feed_title, "articles": articles}


def convert_to_cdt_time(published_time):
    cdt_timezone = pytz.timezone('US/Central')

    # Split the published time string into parts
    parts = published_time.split()

    # Extract date and time components
    date_str = ' '.join(parts[1:4])
    time_str = parts[4]

    # Parse the date and time components
    parsed_time = datetime.strptime(date_str + ' ' + time_str,
                                    "%d %b %Y %H:%M:%S")

    # Set the timezone to CDT
    cdt_time = cdt_timezone.localize(parsed_time)

    return cdt_time.strftime("%a, %d %b %Y %H:%M:%S %Z")


@app.route("/")
def index():
    all_articles = []

    # Fetch RSS feed data in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        feed_data_list = list(executor.map(fetch_feed_data, RSS_FEED_URLS))

    for feed_data in feed_data_list:
        all_articles.extend(feed_data["articles"])

    # Sort articles by publishing time
    all_articles.sort(key=lambda x: x.published_parsed, reverse=True)

    # Convert published times to CDT
    for article in all_articles:
        article.published = convert_to_cdt_time(article.published)

    total_articles = len(all_articles)
    app.logger.info(
        f"Combined and sorted {total_articles} articles from {len(RSS_FEED_URLS)} feeds"
    )

    return render_template("index.html", all_articles=all_articles)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81, debug=True)
