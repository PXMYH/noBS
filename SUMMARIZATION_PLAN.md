# NoBS News Summarization Implementation Plan

## Overview
Implement LLM-based news summarization inspired by the reddit-digest project using the ACE (Agentic Context Engineering) framework. This will transform the raw JSON news data into well-organized, categorized summaries.

## Architecture Analysis from reddit-digest

### Key Components Used:
1. **LiteLLM** - Multi-provider LLM client (OpenRouter, OpenAI, Anthropic, etc.)
2. **ACE Framework** - Agentic Context Engineering for self-improving summaries
3. **Checkpoint System** - Resume-able processing for long-running tasks
4. **Progress Tracking** - tqdm for visual progress
5. **Structured Output** - JSON/Markdown export formats

### Design Patterns:
- **Modular Structure**: Separate fetcher, summarizer, models
- **Resumable Processing**: Checkpoint files for long-running tasks
- **Error Resilience**: Graceful handling of API failures
- **Flexible Models**: Support multiple LLM providers via LiteLLM

## Implementation Plan for NoBS

### Phase 1: Setup and Dependencies
**Goal**: Add necessary dependencies and environment configuration

**Changes**:
1. Add to `pyproject.toml`:
   - `litellm` - Multi-provider LLM client
   - `python-dotenv` (already have it)
   - `tqdm` - Progress bars
   - Optional: `ace-framework` (if we want self-improving summaries)

2. Update `.env.example` with:
   - `OPENROUTER_API_KEY` or `OPENAI_API_KEY`
   - `LLM_MODEL` (default: "openrouter/anthropic/claude-3.5-sonnet")

3. Create `src/config.py` additions for LLM configuration

**Commit**: `feat: add LLM dependencies and configuration for news summarization`

---

### Phase 2: News Categorization and Deduplication
**Goal**: Categorize news articles and remove duplicates

**Changes**:
1. Create `src/news_categorizer.py`:
   - Categories: World/Politics, Finance/Economics/Business, Technology, Sports, Other
   - Keyword-based initial categorization
   - LLM-based refinement for ambiguous articles
   - Deduplication logic (similar titles, same events)

2. Add category classification to Article dataclass in `src/main.py`

**Key Functions**:
```python
def categorize_articles(articles: List[Article]) -> Dict[str, List[Article]]
def deduplicate_by_content(articles: List[Article]) -> List[Article]
def merge_duplicate_reports(articles: List[Article]) -> List[Article]
```

**Commit**: `feat: add news categorization and deduplication logic`

---

### Phase 3: LLM Summarization Module
**Goal**: Create the core summarization engine

**Changes**:
1. Create `src/news_summarizer.py`:
   - LiteLLM client initialization
   - Category-specific prompts
   - Batch processing with checkpoints
   - Error handling and retry logic

2. Prompt templates for each category:
   - **World/Politics**: Focus on key events, impact, countries involved
   - **Finance/Economics/Business**: Market movements, company news, economic indicators
   - **Technology**: Innovations, product launches, industry trends
   - **Sports**: Major events, scores, player news
   - **Other**: General interest stories

**Key Functions**:
```python
class NewsSummarizer:
    def __init__(self, model: str, api_key: str)
    def summarize_category(self, category: str, articles: List[Article]) -> str
    def generate_digest(self, categorized_articles: Dict[str, List[Article]]) -> NewsDigest
```

**Prompts**:
```
For World/Politics:
"Analyze these news articles and write a cohesive 2-3 paragraph summary of major world events.
Group related stories together. Focus on: key events, countries involved, implications.
Articles: {articles}"

For Finance/Economics/Business:
"Summarize these business and economic news articles into 2-3 paragraphs.
Cover: market trends, major company news, economic indicators, business developments.
Articles: {articles}"
```

**Commit**: `feat: implement LLM-based news summarization with category-specific prompts`

---

### Phase 4: Output Generation
**Goal**: Create Markdown digest files

**Changes**:
1. Create `src/digest_generator.py`:
   - Markdown formatting
   - Section headers with emojis
   - Article source citations
   - Date ranges and statistics

2. Output format:
```markdown
# NoBS News Digest - January 3, 2026

Generated from 150 articles across 9 news sources

## 🌍 World & Politics

[2-3 paragraph summary of major world events]

**Key Stories:**
- Venezuela Crisis: US military intervention, Maduro captured...
- North Korea missile tests ahead of Lee-Xi summit...

**Sources**: Bloomberg, NYT, Guardian, WaPo (25 articles)

---

## 💰 Finance, Economics & Business

[2-3 paragraph summary of financial news]

**Key Developments:**
- AI market concerns after DeepSeek announcement...
- Fed rate cut outlook amid economic uncertainty...

**Sources**: WSJ, Bloomberg, CNBC (60 articles)

---

[Continue for other sections...]
```

**Commit**: `feat: add digest output generation with Markdown formatting`

---

### Phase 5: Integration with Main Workflow
**Goal**: Integrate summarization into the existing news pipeline

**Changes**:
1. Update `src/main.py`:
   - Add `--summarize` flag to enable/disable summarization
   - Add summarization step after saving JSON
   - Save digest to `/data/news_digest_YYYY-MM-DD.md`

2. Create new CLI command:
```bash
python src/summarize_news.py --input data/news_source.txt --output data/news_digest.md
```

3. Update `index()` route to optionally generate digest:
```python
if Config.GENERATE_DIGEST:
    # Categorize articles
    categorized = categorize_articles(all_articles)

    # Deduplicate per category
    deduped = {cat: deduplicate_by_content(arts) for cat, arts in categorized.items()}

    # Generate summary
    summarizer = NewsSummarizer(model=Config.LLM_MODEL)
    digest = summarizer.generate_digest(deduped)

    # Save digest
    digest.save_to_file(f'data/news_digest_{today}.md')
```

**Commit**: `feat: integrate news summarization into main workflow`

---

### Phase 6: GitHub Actions Integration
**Goal**: Automate daily digest generation

**Changes**:
1. Update `.github/workflows/pull-bs.yml`:
   - Add LLM API key as secret
   - Add summarization step after JSON generation
   - Commit both JSON and Markdown digest

```yaml
- name: Generate News Digest
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
  run: |
    poetry run python src/summarize_news.py \
      --input data/news_source.txt \
      --output data/news_digest_$(date +%Y-%m-%d).md

- name: Commit and push
  run: |
    git add data/news_source.txt data/news_digest_*.md
    timestamp=$(date -u)
    git commit -m "Latest data and digest: ${timestamp}" || exit 0
    git push
```

2. Update `.gitignore` to track digest files:
```gitignore
# Data directory - keep both JSON and digest files
/data/*
!/data/.gitkeep
!/data/news_source.txt
!/data/news_digest_*.md
```

**Commit**: `feat: add automated digest generation to GitHub Actions`

---

### Phase 7: Documentation and Configuration
**Goal**: Document the new features

**Changes**:
1. Update `CLAUDE.md`:
   - Document summarization architecture
   - Explain category logic
   - Show example digest output

2. Update `README.md` (if exists):
   - Add summarization section
   - Environment variable documentation
   - Cost estimates for different models

3. Create `.env.example`:
```bash
# LLM Configuration
OPENROUTER_API_KEY=sk-or-v1-your-key-here
# or
OPENAI_API_KEY=sk-your-openai-key

# Model selection (default: Claude 3.5 Sonnet via OpenRouter)
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet

# Enable/disable digest generation
GENERATE_DIGEST=true
```

**Commit**: `docs: add summarization documentation and examples`

---

## Configuration Options

### Environment Variables:
- `OPENROUTER_API_KEY` - OpenRouter API key (recommended)
- `OPENAI_API_KEY` - Alternative: Direct OpenAI API key
- `LLM_MODEL` - Model to use (default: "openrouter/anthropic/claude-3.5-sonnet")
- `GENERATE_DIGEST` - Enable/disable digest generation (default: false)
- `MAX_ARTICLES_PER_CATEGORY` - Limit articles per category for summarization (default: 50)

### Model Recommendations:
- **Production**: `openrouter/anthropic/claude-3.5-sonnet` (best quality)
- **Budget**: `openrouter/mistralai/devstral-2512:free` (free tier)
- **Speed**: `openrouter/openai/gpt-4o-mini` (fast and cheap)

---

## Cost Estimates

Using OpenRouter with Claude 3.5 Sonnet:
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens
- Average digest: ~50K input tokens, ~2K output tokens
- **Cost per digest**: ~$0.18

With 150 articles daily:
- **Daily cost**: ~$0.18
- **Monthly cost**: ~$5.40

---

## Testing Strategy

### Phase 2: Categorization
- Test with sample articles from each category
- Verify deduplication catches similar stories
- Check edge cases (mixed topics, unclear categories)

### Phase 3: Summarization
- Test with 5-10 articles per category
- Verify output format and quality
- Test error handling (API failures, rate limits)

### Phase 4: Output
- Verify Markdown formatting
- Check source attribution accuracy
- Test different article counts (0, 1, 100+)

### Phase 5: Integration
- End-to-end test with real news data
- Verify both JSON and digest are generated
- Test with/without API key (graceful degradation)

### Phase 6: GitHub Actions
- Test workflow in fork first
- Verify secrets are properly masked
- Check artifact uploads and commits

---

## Deduplication Strategy

### Techniques:
1. **Exact Title Match**: Remove articles with identical titles
2. **Fuzzy Title Match**: Use Levenshtein distance (85% similarity threshold)
3. **Content Similarity**: Compare first 200 chars of summaries
4. **Entity Detection**: Same key entities (people, places, companies)
5. **LLM Clustering**: Ask LLM to identify duplicate stories

### Implementation:
```python
def deduplicate_by_content(articles: List[Article]) -> List[Article]:
    # Group by fuzzy title match
    groups = cluster_similar_titles(articles)

    # For each group, pick the most comprehensive article
    unique = []
    for group in groups:
        # Sort by content length (longer = more detail)
        sorted_group = sorted(group, key=lambda a: len(a.summary), reverse=True)
        unique.append(sorted_group[0])

    return unique
```

---

## Success Criteria

### Phase 1: ✅ Dependencies added, configuration ready
### Phase 2: ✅ Categories assigned, duplicates removed
### Phase 3: ✅ LLM produces coherent summaries for each category
### Phase 4: ✅ Markdown digest is well-formatted and readable
### Phase 5: ✅ Integration works end-to-end locally
### Phase 6: ✅ GitHub Actions generates and commits digests
### Phase 7: ✅ Documentation is complete and clear

---

## Future Enhancements

### v2.0:
- **Multi-language support**: Translate summaries to other languages
- **Trending topics**: Identify emerging stories
- **Sentiment analysis**: Positive/negative/neutral indicators
- **Source bias detection**: Flag potential bias in reporting

### v3.0:
- **ACE Framework**: Self-improving summaries with skillbook
- **Custom categories**: User-defined categories
- **Interactive web UI**: Browse digests in browser
- **Email delivery**: Daily digest via email

---

## Notes

- Start with **free tier models** for testing (devstral-2512:free)
- Use **checkpoints** for long-running summarizations
- Implement **rate limiting** to respect API quotas
- Add **caching** to avoid re-summarizing same articles
- Consider **local LLMs** (Ollama) for privacy/cost reduction
