# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NoBS is a news aggregation web application that fetches financial, business, and economic news from major news outlets via RSS feeds. It aggregates articles from sources like WSJ, Bloomberg, CNBC, NYT, Guardian, and Washington Post, removes duplicates, and presents them in a clean interface with archive.ph links to bypass paywalls.

## Architecture

### Core Components

- **[src/main.py](src/main.py)**: Flask application serving as the single-page RSS aggregator
  - Fetches feeds in parallel using `concurrent.futures.ThreadPoolExecutor`
  - Uses per-request deduplication (stateless, no global state)
  - Converts HTML summaries to plain text using `html2text`
  - Converts timestamps to configured timezone (default: US/Central)
  - Replaces article links with archive.ph submission URLs to bypass paywalls
  - Generates static `index.html` file on each request
  - Provides `/shutdown` endpoint for graceful shutdown
  - Comprehensive error handling and logging

- **[src/config.py](src/config.py)**: Configuration management
  - Centralizes all configuration settings
  - Supports environment variable overrides
  - RSS feed URLs, timezone, archive service URL, output paths, server settings

- **[templates/index.html](templates/index.html)**: Jinja2 template for the news feed
  - Displays articles with title, published time, and summary
  - Implements swipe-left gesture using Hammer.js to hide articles
  - Uses Chalkboard SE font family for the interface

- **Generated `index.html`**: Static snapshot written to disk on each request, committed to git by CI workflow

### Data Flow

1. Flask endpoint `/` is triggered (either by browser or GitHub Actions)
2. Flask fetches all RSS feeds concurrently (with error handling)
3. Articles converted to Article dataclass objects with validation
4. Articles are deduplicated by title (per-request, stateless)
5. HTML content is converted to plain text
6. Article URLs are converted to archive.ph submission URLs
7. Articles sorted by publication time (newest first)
8. Timestamps converted to configured timezone
9. **Articles saved as JSON to `/data/news_source.txt`** (for GitHub Pages)
10. Template rendered with processed articles (for Flask response)
11. HTML returned to browser

**Client-Side Rendering**:
- Static `index.html` in project root uses JavaScript to fetch `/data/news_source.txt`
- Dynamically renders articles client-side using the JSON data
- Implements swipe-left gesture using Hammer.js to hide articles

### Automated Updates

The GitHub Actions workflow [.github/workflows/pull-bs.yml](.github/workflows/pull-bs.yml) runs hourly (at :27 past each hour):
1. Installs dependencies with Poetry
2. Starts Flask app
3. Curls the root endpoint to trigger JSON generation
4. Waits 1 minute
5. Shuts down the Flask app
6. Verifies `/data/news_source.txt` was created
7. Commits and pushes the updated JSON file if changed

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
python src/main.py
# OR
poetry run python src/main.py

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
- **Source Files**: Located in [src/](src/) directory
- **Configuration**: Centralized in [src/config.py](src/config.py)
  - RSS Feed URLs: List in `Config.RSS_FEED_URLS`
  - Timezone: Configurable via `TIMEZONE` env var (default: US/Central)
  - Archive URL: Configurable via `ARCHIVE_SERVICE_URL` env var
  - Output: Configurable via `OUTPUT_FILENAME` env var (default: absolute path to data/news_source.txt)
  - Server: `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG` env vars
- **Port**: Flask runs on port 5000 (configurable)
- **Debug Mode**: Defaults to False (set `FLASK_DEBUG=true` to enable)

## Important Behaviors

- **Deduplication**: Articles with identical titles are filtered out per-request. Fully stateless - no global state or persistence.
- **Error Handling**: Failed RSS feeds are logged but don't crash the app. Graceful degradation when feeds are unavailable.
- **Archive Links**: All article URLs are automatically converted to archive.ph submission URLs to provide paywall-free access.
- **Data Storage**: Every request to `/` regenerates and overwrites `/data/news_source.txt` with JSON article data. Uses absolute paths for reliability across different working directories.
- **Client-Side Rendering**: Static `index.html` fetches JSON and renders articles dynamically in the browser.
- **No Database**: Application is stateless with no persistent storage beyond the generated JSON file.
- **Type Safety**: Uses dataclasses and type hints for better maintainability.
- **Directory Creation**: The `/data` directory is automatically created if it doesn't exist when saving articles.

## Code Structure

All Python source files are organized in the [src/](src/) directory:
- [src/main.py](src/main.py) - Main Flask application with separated concerns
- [src/config.py](src/config.py) - Configuration with environment variable support
- [src/news_categorizer.py](src/news_categorizer.py) - Article categorization and deduplication
- [src/news_summarizer.py](src/news_summarizer.py) - LLM-powered summarization engine
- [src/summarize_news.py](src/summarize_news.py) - Standalone CLI tool for digest generation

Key architectural improvements:
- **Separated Functions**: Each function has a single responsibility (fetch, process, deduplicate, sort, render)
- **Article Dataclass**: Type-safe representation of news articles
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Error Resilience**: Try-catch blocks prevent crashes from bad feeds
- **Modular Summarization**: Optional LLM integration with graceful degradation

## AI-Powered News Digests

NoBS can automatically generate AI-powered summaries of news articles using LLMs (Large Language Models).

### Features

- **Category-based Organization**: Articles grouped into World/Politics, Finance/Economics, Technology, Sports, and Other
- **Smart Deduplication**: Removes duplicate stories from multiple sources (75% similarity threshold)
- **LLM Summarization**: Generates cohesive 2-3 paragraph summaries per category
- **Multiple LLM Support**: Works with 100+ models via OpenRouter (Claude, GPT-4, Mistral, etc.)
- **Cost Control**: Configurable article limits per category
- **Graceful Degradation**: Works without API key (digests simply won't be generated)

### Setup

1. **Get an API Key** (choose one):
   - OpenRouter (recommended): https://openrouter.ai/keys
   - OpenAI: https://platform.openai.com/api-keys

2. **Configure Environment Variables**:
```bash
# In .env file or environment
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet  # Optional, defaults shown
GENERATE_DIGEST=true  # Enable digest generation
MAX_ARTICLES_PER_CATEGORY=50  # Optional, limits API costs
```

3. **Install Dependencies** (if not already installed):
```bash
poetry install
```

### Usage

#### Standalone CLI Tool

Generate digest from existing JSON data:

```bash
# Basic usage (uses defaults)
python src/summarize_news.py

# Custom paths
python src/summarize_news.py \
  --input data/news_source.txt \
  --output data/custom_digest.md

# Different model
python src/summarize_news.py --model openrouter/openai/gpt-4o

# Verbose logging
python src/summarize_news.py --verbose
```

#### Integrated with Flask

Digests are automatically generated when Flask processes news (if `GENERATE_DIGEST=true`):

```bash
python src/main.py
# Visit http://localhost:5000 to trigger news fetch + digest generation
```

#### GitHub Actions (Automated Daily Digests)

Set up automated hourly digests:

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add repository secret: `OPENROUTER_API_KEY`
3. Optional: Add variable `LLM_MODEL` to customize the model

The workflow will automatically:
- Fetch news hourly
- Generate JSON and Markdown digest
- Commit both files to the repo

### Model Recommendations

| Use Case | Model | Cost per Digest | Notes |
|----------|-------|-----------------|-------|
| **Free Tier** | `openrouter/mistralai/devstral-2512:free` | $0.00 | Good quality, no cost |
| **Best Quality** | `openrouter/anthropic/claude-3.5-sonnet` | ~$0.18 | Most coherent summaries |
| **Fast & Cheap** | `openrouter/openai/gpt-4o-mini` | ~$0.05 | Quick, affordable |
| **Budget** | `openrouter/google/gemini-flash` | ~$0.02 | Very cheap, decent quality |

Monthly costs (30 days):
- Free tier: $0.00
- Claude 3.5 Sonnet: ~$5.40/month
- GPT-4o Mini: ~$1.50/month

### Output Format

Digests are saved as Markdown files (`data/news_digest_YYYY-MM-DD.md`) with:

- **Header**: Date, article counts, source statistics
- **Category Sections**: World/Politics, Finance/Economics, Technology, Sports, Other
- **Per Category**:
  - 2-3 paragraph AI-generated summary
  - Key stories bullet points
  - Source attribution and article counts
- **Footer**: Generation timestamp

Example excerpt:
```markdown
# NoBS News Digest - January 3, 2026

Generated from **150** unique articles (deduplicated from 180 total) across **9** news sources

---

## 🌍 World & Politics

The United States launched military strikes against Venezuela, capturing
President Nicolás Maduro in an early morning raid. President Trump announced
that American oil companies will invest billions to rebuild Venezuela's oil
infrastructure...

**Key Stories:**
- Venezuela Crisis: US military intervention, Maduro captured and indicted
- North Korea missile tests ahead of Lee-Xi summit
- Berlin power outage from suspected arson affects 50,000 homes

**Sources**: Bloomberg, NYT, Guardian, WaPo (25 articles)

---

## 💰 Finance, Economics & Business

[Summary content...]
```

### Categories

1. **🌍 World & Politics**: Government actions, diplomatic events, military operations
2. **💰 Finance, Economics & Business**: Markets, Fed actions, company news, economic indicators
3. **💻 Technology**: AI developments, tech companies, product launches, innovation
4. **⚽ Sports**: Games, player news, league developments (if present in sources)
5. **📰 Other News**: General interest, cultural, social news

### Troubleshooting

**Digest not generating?**
- Check if `GENERATE_DIGEST=true` is set
- Verify API key is configured (`OPENROUTER_API_KEY` or `OPENAI_API_KEY`)
- Check logs for errors: `python src/main.py` (look for "=== Starting digest generation ===")
- Test standalone: `python src/summarize_news.py --verbose`

**API costs too high?**
- Use free tier model: `LLM_MODEL=openrouter/mistralai/devstral-2512:free`
- Reduce articles per category: `MAX_ARTICLES_PER_CATEGORY=25`
- Disable digest: `GENERATE_DIGEST=false`

**Digest quality issues?**
- Try Claude 3.5 Sonnet for best quality: `LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet`
- Check article quality - garbage in, garbage out
- Ensure sufficient articles per category (< 5 articles may produce weak summaries)

## Adding New RSS Feeds

To add new feeds, append URLs to the `RSS_FEED_URLS` list in [src/config.py](src/config.py). Ensure feeds follow standard RSS format and include `title`, `link`, `published`, and `summary` fields.
