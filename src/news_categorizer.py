"""
News categorizer and deduplication module for NoBS News Aggregator.

Categorizes articles into sections and removes duplicate stories.
"""

import re
from typing import Dict, List, Set
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class CategoryKeywords:
    """Keywords for categorizing news articles."""

    world_politics: Set[str] = None
    finance_economics: Set[str] = None
    technology: Set[str] = None
    sports: Set[str] = None

    def __post_init__(self):
        """Initialize keyword sets."""
        self.world_politics = {
            'president', 'government', 'election', 'senate', 'congress', 'parliament',
            'minister', 'diplomatic', 'treaty', 'war', 'military', 'defense', 'nato',
            'united nations', 'summit', 'sanctions', 'refugee', 'border', 'immigration',
            'coup', 'protest', 'democracy', 'authoritarian', 'sovereignty', 'geopolitical',
            'embassy', 'foreign policy', 'intervention', 'occupied', 'annexation', 'regime',
            'venezuela', 'china', 'russia', 'ukraine', 'taiwan', 'north korea',
            'strikes', 'airstrikes', 'military operation', 'captured', 'indicted'
        }

        self.finance_economics = {
            'stock', 'market', 'trading', 'investor', 'shares', 'equity', 'bond',
            'dollar', 'currency', 'forex', 'fed', 'federal reserve', 'interest rate',
            'inflation', 'deflation', 'gdp', 'unemployment', 'jobs report', 'earnings',
            'revenue', 'profit', 'loss', 'merger', 'acquisition', 'ipo', 'nasdaq',
            's&p', 'dow jones', 'wall street', 'ceo', 'cfo', 'corporation',
            'bankruptcy', 'debt', 'credit', 'loan', 'mortgage', 'real estate',
            'bank', 'banking', 'financial', 'economy', 'economic', 'business',
            'company', 'firm', 'enterprise', 'startup', 'unicorn', 'valuation',
            'tariff', 'trade', 'export', 'import', 'commodity', 'oil', 'gold',
            'silver', 'crypto', 'bitcoin', 'retail', 'consumer', 'spending'
        }

        self.technology = {
            'tech', 'technology', 'software', 'hardware', 'app', 'application',
            'ai', 'artificial intelligence', 'machine learning', 'deepseek', 'chatgpt',
            'openai', 'anthropic', 'google', 'microsoft', 'apple', 'meta', 'amazon',
            'nvidia', 'chip', 'semiconductor', 'processor', 'gpu', 'cloud computing',
            'cybersecurity', 'hack', 'breach', 'data privacy', 'encryption',
            'smartphone', 'iphone', 'android', 'tablet', 'laptop', 'computer',
            'internet', 'broadband', '5g', 'wireless', 'satellite', 'spacex',
            'electric vehicle', 'ev', 'tesla', 'autonomous', 'robotaxi',
            'social media', 'twitter', 'facebook', 'instagram', 'tiktok',
            'algorithm', 'blockchain', 'nft', 'metaverse', 'vr', 'ar'
        }

        self.sports = {
            'nfl', 'nba', 'mlb', 'nhl', 'soccer', 'football', 'basketball',
            'baseball', 'hockey', 'tennis', 'golf', 'olympics', 'world cup',
            'championship', 'playoffs', 'season', 'game', 'match', 'tournament',
            'athlete', 'player', 'coach', 'team', 'league', 'draft', 'trade',
            'injury', 'score', 'win', 'defeat', 'victory', 'champion'
        }


CATEGORY_KEYWORDS = CategoryKeywords()


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by converting to lowercase and removing punctuation.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    return re.sub(r'[^\w\s]', '', text.lower())


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity ratio between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    normalized1 = normalize_text(text1)
    normalized2 = normalize_text(text2)
    return SequenceMatcher(None, normalized1, normalized2).ratio()


def categorize_article(title: str, summary: str) -> str:
    """
    Categorize an article based on keywords in title and summary.

    Categories:
    - world_politics: World events, political news
    - finance_economics: Markets, business, economy
    - technology: Tech companies, innovation, AI
    - sports: Sports news and events
    - other: Everything else

    Args:
        title: Article title
        summary: Article summary

    Returns:
        Category name
    """
    # Combine title and summary for analysis (title has more weight)
    text = (title.lower() * 3) + ' ' + summary.lower()

    # Count keyword matches for each category
    scores = {
        'world_politics': sum(1 for kw in CATEGORY_KEYWORDS.world_politics if kw in text),
        'finance_economics': sum(1 for kw in CATEGORY_KEYWORDS.finance_economics if kw in text),
        'technology': sum(1 for kw in CATEGORY_KEYWORDS.technology if kw in text),
        'sports': sum(1 for kw in CATEGORY_KEYWORDS.sports if kw in text),
    }

    # Get category with highest score
    max_score = max(scores.values())

    # If no strong category match (score < 2), mark as 'other'
    if max_score < 2:
        return 'other'

    # Return category with highest score
    return max(scores, key=scores.get)


def categorize_articles(articles: List) -> Dict[str, List]:
    """
    Categorize a list of articles into sections.

    Args:
        articles: List of Article objects

    Returns:
        Dictionary mapping category names to lists of articles
    """
    categorized = {
        'world_politics': [],
        'finance_economics': [],
        'technology': [],
        'sports': [],
        'other': []
    }

    for article in articles:
        category = categorize_article(article.title, article.summary)
        categorized[category].append(article)

    return categorized


def find_duplicate_groups(articles: List, similarity_threshold: float = 0.75) -> List[List]:
    """
    Group similar articles together based on title similarity.

    Args:
        articles: List of Article objects
        similarity_threshold: Similarity threshold for grouping (0.0-1.0)

    Returns:
        List of article groups (each group is a list of similar articles)
    """
    if not articles:
        return []

    groups = []
    used_indices = set()

    for i, article1 in enumerate(articles):
        if i in used_indices:
            continue

        # Start a new group with this article
        group = [article1]
        used_indices.add(i)

        # Find similar articles
        for j, article2 in enumerate(articles[i + 1:], start=i + 1):
            if j in used_indices:
                continue

            similarity = calculate_similarity(article1.title, article2.title)
            if similarity >= similarity_threshold:
                group.append(article2)
                used_indices.add(j)

        groups.append(group)

    return groups


def pick_best_article(group: List) -> object:
    """
    Pick the best article from a group of duplicates.

    Selection criteria (in order):
    1. Longest summary (more detailed)
    2. Highest score (more popular)
    3. Most comments (more discussion)

    Args:
        group: List of similar Article objects

    Returns:
        Best Article from the group
    """
    if len(group) == 1:
        return group[0]

    # Sort by summary length (descending), then score, then comments
    sorted_group = sorted(
        group,
        key=lambda a: (len(a.summary), getattr(a, 'score', 0), getattr(a, 'num_comments', 0)),
        reverse=True
    )

    return sorted_group[0]


def deduplicate_articles(articles: List, similarity_threshold: float = 0.75) -> List:
    """
    Remove duplicate articles based on title similarity.

    Args:
        articles: List of Article objects
        similarity_threshold: Similarity threshold for deduplication (0.0-1.0)

    Returns:
        List of unique Article objects
    """
    if not articles:
        return []

    # Group similar articles
    groups = find_duplicate_groups(articles, similarity_threshold)

    # Pick best article from each group
    unique_articles = [pick_best_article(group) for group in groups]

    return unique_articles


def deduplicate_by_category(categorized_articles: Dict[str, List]) -> Dict[str, List]:
    """
    Deduplicate articles within each category.

    Args:
        categorized_articles: Dictionary mapping categories to article lists

    Returns:
        Dictionary with deduplicated articles per category
    """
    deduped = {}

    for category, articles in categorized_articles.items():
        deduped[category] = deduplicate_articles(articles)

    return deduped


def get_duplicate_count(articles: List, similarity_threshold: float = 0.75) -> int:
    """
    Count how many articles are duplicates.

    Args:
        articles: List of Article objects
        similarity_threshold: Similarity threshold for deduplication

    Returns:
        Number of duplicate articles removed
    """
    original_count = len(articles)
    unique_count = len(deduplicate_articles(articles, similarity_threshold))
    return original_count - unique_count
