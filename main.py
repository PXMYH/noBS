from flask import Flask, render_template, request, jsonify
import feedparser
import concurrent.futures
import logging
import pytz
from datetime import datetime
import os
import html2text
import urllib.parse
from dataclasses import dataclass
from typing import Optional
from config import Config

app = Flask(__name__)

# Configure Flask's logger
app.logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
app.logger.addHandler(handler)


@dataclass
class Article:
    """Represents a news article from RSS feed."""
    title: str
    link: str
    published: str
    summary: str
    published_parsed: Optional[tuple] = None

    @classmethod
    def from_feed_entry(cls, entry):
        """Create Article from feedparser entry with validation."""
        return cls(
            title=getattr(entry, 'title', 'Untitled'),
            link=getattr(entry, 'link', ''),
            published=getattr(entry, 'published', ''),
            summary=getattr(entry, 'summary', ''),
            published_parsed=getattr(entry, 'published_parsed', None)
        )


def validate_article(article):
    """Check if article has required fields."""
    return (
        hasattr(article, 'title') and article.title and
        hasattr(article, 'link') and article.link and
        hasattr(article, 'published') and
        hasattr(article, 'summary')
    )


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
    """Convert published time to configured timezone with error handling."""
    try:
        cdt_timezone = pytz.timezone(Config.TIMEZONE)

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
    h.ignore_links = Config.HTML2TEXT_IGNORE_LINKS

    # Convert the HTML content to plain text
    text_content = h.handle(html_content)

    return text_content


def fetch_all_feeds(feed_urls):
    """Fetch all RSS feeds in parallel and filter out failures."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        feed_data_list = list(executor.map(fetch_feed_data, feed_urls))

    # Filter out None results from failed feeds
    return [feed for feed in feed_data_list if feed is not None]


def transform_article_url(url):
    """Transform article URL to archive service URL."""
    url_without_query = url.split('?')[0]
    encoded_url = urllib.parse.quote_plus(url_without_query)
    return Config.ARCHIVE_SERVICE_URL + encoded_url


def process_articles(feed_data_list):
    """Process articles from feed data: convert to Article objects, transform URLs and clean HTML."""
    all_articles = []

    for feed_data in feed_data_list:
        for entry in feed_data["articles"]:
            # Validate entry has required fields
            if not validate_article(entry):
                continue

            # Create Article from feed entry
            article = Article.from_feed_entry(entry)

            # Transform article URL to archive URL
            article.link = transform_article_url(article.link)

            # Clean the HTML content to remove tags
            article.summary = clean_html(article.summary)

            all_articles.append(article)

    return all_articles


def sort_by_date(articles):
    """Sort articles by publication time (newest first)."""
    articles.sort(key=lambda x: x.published_parsed, reverse=True)
    return articles


def convert_article_times(articles):
    """Convert all article published times to configured timezone."""
    for article in articles:
        article.published = convert_to_cdt_time(article.published)
    return articles


def render_html(articles):
    """Render the HTML template with articles."""
    return render_template("index.html", all_articles=articles)


@app.route("/")
def index():
    """Main route: fetch, process, and render news articles."""
    # Fetch feeds
    feed_data_list = fetch_all_feeds(Config.RSS_FEED_URLS)

    # Process articles
    all_articles = process_articles(feed_data_list)

    # Deduplicate
    all_articles = deduplicate_articles(all_articles)

    # Sort by date
    all_articles = sort_by_date(all_articles)

    # Convert times to configured timezone
    all_articles = convert_article_times(all_articles)

    # Log
    app.logger.info(
        f"Displaying {len(all_articles)} unique articles from {len(feed_data_list)} feeds"
    )

    # Render
    html = render_html(all_articles)

    # Save
    save_html_to_file(html)

    return html


@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Shutdown the Flask app gracefully
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
    return jsonify({'message': 'Shutting down...'})


# Function to save rendered HTML to a file
def save_html_to_file(html_content):
    with open(Config.OUTPUT_FILENAME, 'w', encoding='utf-8') as file:
        file.write(html_content)


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
