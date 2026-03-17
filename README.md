# Researcher

A Claude Code skill and toolkit for autonomous multi-source research. Given a query, it launches parallel sub-agents that search the web, encyclopedia, and public datasets — then synthesizes everything into a structured Markdown report with optional charts, infographics, and DOCX/PDF export.

## How it works

Invoke with `/researcher <query>` inside Claude Code. The agent will:

1. Check vector memory for similar past research
2. Check the `docs/` folder for relevant local documents
3. Launch parallel sub-agents (web search, encyclopedia, data)
4. Run up to 3 research rounds
5. Optionally generate a chart (Datawrapper) or infographic (Krea)
6. Write `answer.md` + `sources.md` to `queries/<slug>/`
7. Save the result to semantic memory (Chroma)
8. Optionally export to DOCX or PDF

The response language matches the query language automatically.

## Requirements

- Python 3.12+
- [Claude Code](https://claude.ai/code)
- [pandoc](https://pandoc.org/) (for DOCX/PDF export)
- Playwright Chromium (for JS-rendered pages)

## Setup

```bash
# Clone and create virtual environment
git clone https://github.com/your-username/researcher
cd researcher
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install playwright requests beautifulsoup4 chromadb wikipedia \
            firecrawl-py python-dotenv pypandoc

# Install Playwright browser
playwright install chromium

# Install CLI tools
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env and fill in your keys
```

## API keys

| Key | Required | Used for |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Semantic memory embeddings |
| `FIRECRAWL_API_KEY` | Yes | Web search + scraping |
| `DATAWRAPPER_API_KEY` | Optional | Charts |
| `KREA_API_KEY` | Optional | Infographic generation |

## CLI tools

All tools are available as CLI commands after `pip install -e .`:

```bash
researcher-search "query" [--max 10] [--region en-us]
researcher-browse "https://example.com" [--max 5000]
researcher-wiki "query" [--lang en] [--sentences 5] [--full]
researcher-polona "query" [--size 10] [--sort oldest]   # Polish National Library
researcher-dane "query" [--per-page 5] [--resources]    # Polish open data portal
researcher-firecrawl "query" [--limit 5] [--scrape]
researcher-list
researcher-export <slug> [--docx] [--pdf]
```

## Output structure

```
queries/
  2024-01-15_air-quality-trends/
    answer.md       # Full research report
    sources.md      # All sources with URLs
    answer.docx     # (optional export)
    answer.pdf      # (optional export)
    img/
      infographic.png
```

## Examples

Two completed research reports are included in [`examples_of_finished_queries/`](./examples_of_finished_queries/):

- **[Steam games market report 2025](./examples_of_finished_queries/2026-03-15_gry-steam-2025-raport/answer.md)** — quantitative market analysis with data from 21,473 games
- **[Oscars 2026 summary](./examples_of_finished_queries/2026-03-16_oscary-2026-podsumowanie/answer.md)** — event coverage with infographic

---

## Notes on regional tools

`researcher-polona` and `researcher-dane` are oriented towards Polish open data sources. They can be replaced or supplemented with equivalents for other countries.

## License

MIT
