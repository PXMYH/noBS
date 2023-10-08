from flask import Flask, render_template
import feedparser
import concurrent.futures

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


def fetch_feed_data(url):
    feed = feedparser.parse(url)
    feed_title = feed.feed.title
    articles = feed.entries
    return {"feed_title": feed_title, "articles": articles}


@app.route("/")
def index():
    all_feed_data = []

    # Fetch RSS feed data in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        feed_data_list = list(executor.map(fetch_feed_data, RSS_FEED_URLS))

    total_feeds = len(RSS_FEED_URLS)

    for i, feed_data in enumerate(feed_data_list, start=1):
        print(f"Processed {i}/{total_feeds} feeds")
        all_feed_data.append(feed_data)

    print("Finished processing all feeds")

    return render_template("index.html", all_feed_data=all_feed_data)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=81, debug=True)
