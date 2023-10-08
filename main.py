from flask import Flask, render_template
import feedparser

app = Flask(__name__)

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


@app.route("/")
def index():
    # Initialize an empty list to store feed data
    all_feed_data = []

    # Fetch and parse each RSS feed URL
    for url in RSS_FEED_URLS:
        feed = feedparser.parse(url)
        feed_title = feed.feed.title
        articles = feed.entries

        # Store the feed data in a dictionary
        feed_data = {"feed_title": feed_title, "articles": articles}

        # Append the feed data to the list
        all_feed_data.append(feed_data)

    return render_template("index.html", all_feed_data=all_feed_data)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81, debug=True)
