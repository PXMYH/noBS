"""
LLM-powered news summarizer for NoBS News Aggregator.

Uses LiteLLM to generate category-specific summaries from multiple articles.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    completion = None

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None


@dataclass
class CategorySummary:
    """Summary for a news category."""
    category: str
    summary_text: str
    article_count: int
    key_stories: List[str]
    sources: List[str]
    articles: List = None  # Store actual articles for linking


@dataclass
class NewsDigest:
    """Complete news digest with all categories."""
    date: datetime
    categories: List[CategorySummary]
    total_articles: int
    total_unique_articles: int
    sources: List[str]


class NewsSummarizer:
    """
    Summarizes categorized news articles using LLM.
    """

    # Category display names and emojis
    CATEGORY_INFO = {
        'world_politics': {
            'name': 'World & Politics',
            'emoji': '🌍',
            'description': 'Major world events, political developments, and diplomatic news'
        },
        'finance_economics': {
            'name': 'Finance, Economics & Business',
            'emoji': '💰',
            'description': 'Markets, economy, business news, and corporate developments'
        },
        'technology': {
            'name': 'Technology',
            'emoji': '💻',
            'description': 'Tech companies, innovation, AI, and digital developments'
        },
        'sports': {
            'name': 'Sports',
            'emoji': '⚽',
            'description': 'Sports events, games, and athletic news'
        },
        'other': {
            'name': 'Other News',
            'emoji': '📰',
            'description': 'Miscellaneous news and stories'
        }
    }

    def __init__(
        self,
        model: str = "openrouter/anthropic/claude-3.5-sonnet",
        api_key: Optional[str] = None,
        max_articles_per_category: int = 50
    ):
        """
        Initialize the news summarizer.

        Args:
            model: LLM model to use (default: Claude 3.5 Sonnet via OpenRouter)
            api_key: API key for the LLM provider (optional, uses env var)
            max_articles_per_category: Maximum articles to summarize per category
        """
        if not LITELLM_AVAILABLE:
            raise ImportError(
                "litellm is not installed. Install with: pip install litellm"
            )

        self.model = model
        self.api_key = api_key
        self.max_articles_per_category = max_articles_per_category
        self.logger = logging.getLogger(__name__)

    def _get_category_prompt(self, category: str, articles: List) -> str:
        """
        Generate category-specific prompt for summarization.

        Args:
            category: Category name
            articles: List of Article objects

        Returns:
            Prompt string for the LLM
        """
        # Prepare articles list
        articles_text = ""
        for i, article in enumerate(articles[:self.max_articles_per_category], 1):
            articles_text += f"\n{i}. **{article.title}**\n"
            articles_text += f"   Source: {article.link.split('/')[2] if '/' in article.link else 'Unknown'}\n"
            articles_text += f"   Published: {article.published}\n"
            articles_text += f"   Summary: {article.summary[:300]}...\n"

        # Category-specific instructions
        if category == 'world_politics':
            focus = """Focus on:
- Major geopolitical events and their implications
- Political developments and government actions
- International relations and diplomatic activities
- Military operations and conflicts
- Key players (leaders, countries, organizations)"""

        elif category == 'finance_economics':
            focus = """Focus on:
- Market movements and trends (stocks, bonds, commodities)
- Economic indicators and Fed/central bank actions
- Major business deals, M&A, IPOs
- Corporate earnings and business performance
- Economic policy and its impact"""

        elif category == 'technology':
            focus = """Focus on:
- Major tech announcements and product launches
- AI developments and innovations
- Tech company news (earnings, leadership, strategy)
- Regulatory and legal developments affecting tech
- Emerging trends and disruptive technologies"""

        elif category == 'sports':
            focus = """Focus on:
- Major games, matches, and tournament results
- Notable player performances and achievements
- Team news, trades, and roster changes
- Sports business and league developments
- Upcoming significant events"""

        else:  # other
            focus = """Focus on:
- Key themes and interesting developments
- Notable human interest stories
- Cultural or social significance
- Emerging trends worth noting"""

        prompt = f"""You are a professional news editor creating a daily digest. Analyze these {len(articles[:self.max_articles_per_category])} articles and write a cohesive 2-3 paragraph summary.

{focus}

Important guidelines:
- Write in clear, journalistic style
- Group related stories together naturally
- Highlight the most newsworthy developments
- Avoid redundancy when multiple sources cover the same story
- Be concise but informative
- Use present tense for recent events

Articles to summarize:
{articles_text}

Provide ONLY the JSON response without any markdown formatting or code blocks. Use this exact format:
{{
    "summary": "2-3 paragraph cohesive summary here",
    "key_stories": [
        "Brief headline 1",
        "Brief headline 2",
        "Brief headline 3"
    ]
}}

Only include 3-5 key stories. Make the summary flow naturally, not as a list. Do not wrap the JSON in markdown code blocks."""

        return prompt

    def summarize_category(
        self,
        category: str,
        articles: List
    ) -> Optional[CategorySummary]:
        """
        Summarize articles in a single category.

        Args:
            category: Category name
            articles: List of Article objects

        Returns:
            CategorySummary or None if summarization fails
        """
        if not articles:
            return None

        # Limit articles to prevent excessive API costs
        articles_to_process = articles[:self.max_articles_per_category]

        try:
            # Generate prompt
            prompt = self._get_category_prompt(category, articles_to_process)

            # Call LLM
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                temperature=0.3,  # Lower temperature for more consistent output
            )

            # Parse response
            content = response.choices[0].message.content

            # Try to parse JSON (handle both raw JSON and markdown code blocks)
            try:
                # Remove markdown code block markers if present
                if content.strip().startswith("```"):
                    # Extract content between code blocks
                    lines = content.strip().split('\n')
                    # Remove first line (```json or ```) and last line (```)
                    json_content = '\n'.join(lines[1:-1])
                else:
                    json_content = content

                result = json.loads(json_content)
                summary_text = result.get("summary", "")
                key_stories = result.get("key_stories", [])
            except (json.JSONDecodeError, IndexError) as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                # Fallback: use raw content as summary
                summary_text = content
                key_stories = []

            # Extract unique sources
            sources = list(set(
                article.link.split('/')[2] if '/' in article.link else 'Unknown'
                for article in articles_to_process
            ))

            return CategorySummary(
                category=category,
                summary_text=summary_text,
                article_count=len(articles),
                key_stories=key_stories,
                sources=sorted(sources),
                articles=articles_to_process  # Include articles for linking
            )

        except Exception as e:
            self.logger.error(f"Error summarizing {category}: {e}")
            return None

    def generate_digest(
        self,
        categorized_articles: Dict[str, List],
        show_progress: bool = True
    ) -> NewsDigest:
        """
        Generate complete news digest from categorized articles.

        Args:
            categorized_articles: Dictionary mapping categories to article lists
            show_progress: Whether to show progress bar

        Returns:
            NewsDigest with all category summaries
        """
        category_summaries = []
        total_articles = sum(len(arts) for arts in categorized_articles.values())

        # Collect all unique sources
        all_sources = set()
        for articles in categorized_articles.values():
            for article in articles:
                source = article.link.split('/')[2] if '/' in article.link else 'Unknown'
                all_sources.add(source)

        # Process each category
        categories_to_process = [
            (cat, arts) for cat, arts in categorized_articles.items()
            if arts  # Only process non-empty categories
        ]

        if show_progress and TQDM_AVAILABLE:
            iterator = tqdm(categories_to_process, desc="Summarizing categories", unit="category")
        else:
            iterator = categories_to_process
            if show_progress:
                print(f"\nSummarizing {len(categories_to_process)} categories...")

        for category, articles in iterator:
            if show_progress and TQDM_AVAILABLE:
                cat_name = self.CATEGORY_INFO[category]['name']
                iterator.set_postfix_str(f"{cat_name} ({len(articles)} articles)")

            summary = self.summarize_category(category, articles)
            if summary:
                category_summaries.append(summary)

        # Calculate unique articles (after deduplication)
        total_unique = sum(len(arts) for arts in categorized_articles.values())

        digest = NewsDigest(
            date=datetime.now(),
            categories=category_summaries,
            total_articles=total_articles,
            total_unique_articles=total_unique,
            sources=sorted(list(all_sources))
        )

        return digest

    def format_digest_markdown(self, digest: NewsDigest) -> str:
        """
        Format digest as Markdown.

        Args:
            digest: NewsDigest to format

        Returns:
            Markdown-formatted string
        """
        md = f"# NoBS News Digest - {digest.date.strftime('%B %d, %Y')}\n\n"
        md += f"Generated from **{digest.total_unique_articles}** unique articles "
        md += f"(deduplicated from {digest.total_articles} total) "
        md += f"across **{len(digest.sources)}** news sources\n\n"

        md += "---\n\n"

        # Add each category
        for cat_summary in digest.categories:
            info = self.CATEGORY_INFO[cat_summary.category]

            md += f"## {info['emoji']} {info['name']}\n\n"
            md += f"{cat_summary.summary_text}\n\n"

            # Add top articles as clickable links
            if cat_summary.articles:
                md += "**Top Articles:**\n"
                # Show top 5 articles with links
                for article in cat_summary.articles[:5]:
                    md += f"- [{article.title}]({article.link})\n"
                md += "\n"

            md += f"**Sources**: {', '.join(cat_summary.sources)} "
            md += f"({cat_summary.article_count} article{'s' if cat_summary.article_count != 1 else ''})\n\n"
            md += "---\n\n"

        # Footer
        md += f"*Digest generated on {digest.date.strftime('%B %d, %Y at %I:%M %p %Z')}*\n"

        return md
