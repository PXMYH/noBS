# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NoBS is a news aggregation web application that fetches financial, business, and economic news from major news outlets via RSS feeds. It aggregates articles from sources like WSJ, Bloomberg, CNBC, NYT, Guardian, and Washington Post, removes duplicates, and presents them in a clean interface with archive.ph links to bypass paywalls.

## Architecture

### Core Components

- **[main.py](main.py)**: Flask application serving as the single-page RSS aggregator
  - Fetches feeds in parallel using `concurrent.futures.ThreadPoolExecutor`
  - Maintains in-memory `unique_article_titles` set to deduplicate articles
  - Converts HTML summaries to plain text using `html2text`
  - Converts timestamps to US/Central timezone
  - Replaces article links with archive.ph submission URLs to bypass paywalls
  - Generates static `index.html` file on each request
  - Provides `/shutdown` endpoint for graceful shutdown

- **[templates/index.html](templates/index.html)**: Jinja2 template for the news feed
  - Displays articles with title, published time, and summary
  - Implements swipe-left gesture using Hammer.js to hide articles
  - Uses Chalkboard SE font family for the interface

- **Generated `index.html`**: Static snapshot written to disk on each request, committed to git by CI workflow

### Data Flow

1. Browser hits root endpoint `/`
2. Flask fetches all RSS feeds concurrently
3. Articles are deduplicated by title (in-memory set)
4. HTML content is converted to plain text
5. Article URLs are converted to archive.ph submission URLs
6. Articles sorted by publication time (newest first)
7. Timestamps converted to US/Central timezone
8. Template rendered with processed articles
9. Rendered HTML saved to `index.html` file
10. HTML returned to browser

### Automated Updates

The GitHub Actions workflow [.github/workflows/pull-bs.yml](.github/workflows/pull-bs.yml) runs hourly (at :27 past each hour):
1. Installs dependencies with Poetry
2. Starts Flask app
3. Curls the root endpoint to trigger HTML generation
4. Waits 1 minute
5. Shuts down the Flask app
6. Commits and pushes the updated `index.html` if changed

## Development Commands

### Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Running the Application
```bash
# Run Flask development server
python main.py
# OR
poetry run python main.py

# Application runs on http://0.0.0.0:5000
```

### Linting
```bash
# Run ruff linter
poetry run ruff check .

# Type checking with pyright
poetry run pyright
```

## Key Configuration

- **Python Version**: 3.10.x (specified in [pyproject.toml](pyproject.toml))
- **RSS Feed URLs**: Hardcoded list `RSS_FEED_URLS` in [main.py](main.py:21-31)
- **Timezone**: All timestamps converted to US/Central
- **Port**: Flask runs on port 5000
- **Deployment**: Configured for Google Cloud Run (see [.replit](.replit))

## Important Behaviors

- **Deduplication**: Articles with identical titles are filtered out within a single request. The `unique_article_titles` set is reset on each request (not persistent across restarts).
- **Archive Links**: All article URLs are automatically converted to archive.ph submission URLs to provide paywall-free access.
- **Static Generation**: Every request to `/` regenerates and overwrites `index.html` on disk.
- **No Database**: Application is stateless with no persistent storage beyond the generated HTML file.

## Adding New RSS Feeds

To add new feeds, append URLs to the `RSS_FEED_URLS` list in [main.py](main.py:21-31). Ensure feeds follow standard RSS format and include `title`, `link`, `published`, and `summary` fields.
