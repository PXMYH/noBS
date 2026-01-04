from flask import Flask, render_template, request, jsonify
import feedparser
import concurrent.futures
import logging
import pytz
from datetime import datetime
import os
import html2text
import urllib.parse  # Import urllib.parse

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
    """Fetch RSS feed data with error handling."""
    try:
        feed = feedparser.parse(url)
        if not hasattr(feed, 'feed') or not hasattr(feed.feed, 'title'):
            app.logger.warning(f"Invalid feed structure from {url}")
            return None
        return {
            "feed_title": feed.feed.title,
            "articles": feed.entries
        }
    except Exception as e:
        app.logger.error(f"Failed to fetch feed {url}: {str(e)}")
        return None


def convert_to_cdt_time(published_time):
    """Convert published time to US/Central timezone with error handling."""
    try:
        cdt_timezone = pytz.timezone('US/Central')

        # Split the published time string into parts
        parts = published_time.split()

        if len(parts) < 5:
            return published_time  # Return original if can't parse

        # Extract date and time components
        date_str = ' '.join(parts[1:4])
        time_str = parts[4]

        # Parse the date and time components
        parsed_time = datetime.strptime(date_str + ' ' + time_str,
                                        "%d %b %Y %H:%M:%S")

        # Set the timezone to CDT
        cdt_time = cdt_timezone.localize(parsed_time)

        return cdt_time.strftime("%a, %d %b %Y %H:%M:%S %Z")
    except (ValueError, IndexError) as e:
        app.logger.warning(f"Failed to convert time '{published_time}': {str(e)}")
        return published_time  # Fallback to original


def deduplicate_articles(articles):
    """Remove duplicate articles based on title (per-request deduplication)."""
    seen = set()
    unique = []
    for article in articles:
        if hasattr(article, 'title') and article.title not in seen:
            seen.add(article.title)
            unique.append(article)
    return unique


def clean_html(html_content):
    # Create an instance of the html2text converter
    h = html2text.HTML2Text()
    h.ignore_links = True  # Ignore links in the content

    # Convert the HTML content to plain text
    text_content = h.handle(html_content)

    return text_content


@app.route("/")
def index():
    all_articles = []

    # Fetch RSS feed data in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        feed_data_list = list(executor.map(fetch_feed_data, RSS_FEED_URLS))

    # Filter out None results from failed feeds
    feed_data_list = [feed for feed in feed_data_list if feed is not None]

    for feed_data in feed_data_list:
        for article in feed_data["articles"]:
            # Encode the article.link to create archive_request_url
            url_without_query = article.link.split('?')[0]
            url = urllib.parse.quote_plus(url_without_query)
            archive_request_url = 'https://archive.ph/submit/?url=' + url

            # Clean the HTML content to remove tags
            article.summary = clean_html(article.summary)
            # Replace the article.link with archive_request_url
            article.link = archive_request_url

            all_articles.append(article)

    # Deduplicate articles by title (per-request)
    all_articles = deduplicate_articles(all_articles)

    # Sort articles by publishing time
    all_articles.sort(key=lambda x: x.published_parsed, reverse=True)

    # Convert published times to CDT
    for article in all_articles:
        article.published = convert_to_cdt_time(article.published)

    total_articles = len(all_articles)
    app.logger.info(
        f"Combined and sorted {total_articles} unique articles from {len(feed_data_list)} feeds"
    )

    # Render the HTML template with the modified article.link values
    rendered_html = render_template("index.html", all_articles=all_articles)

    # Save the rendered HTML to a file with the name index.html
    save_html_to_file(rendered_html)

    return rendered_html


@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Shutdown the Flask app gracefully
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
    return jsonify({'message': 'Shutting down...'})


# Function to save rendered HTML to a file
def save_html_to_file(html_content):
    with open("index.html", 'w', encoding='utf-8') as file:
        file.write(html_content)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
