"""
Web search and scraping tool using Firecrawl API.
Documentation: https://docs.firecrawl.dev/features/search
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.firecrawl.dev/v1"


def _headers() -> dict:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not found in environment variables")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def search(query: str, limit: int = 5, lang: str = "en", country: str = "us") -> list[dict]:
    """
    Search the web via Firecrawl.

    Args:
        query: Search query
        limit: Number of results (default 5, max 10)
        lang: Result language (default 'en')
        country: Result country (default 'us')

    Returns:
        List of results with url, title, description
    """
    payload = {
        "query": query,
        "limit": limit,
        "lang": lang,
        "country": country,
    }

    response = requests.post(f"{BASE_URL}/search", headers=_headers(), json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"Firecrawl error: {data.get('error')}")

    return data.get("data", [])


def scrape(url: str, only_main_content: bool = True) -> dict:
    """
    Fetch page content as Markdown.

    Args:
        url: Page URL to scrape
        only_main_content: Whether to extract only main content (without nav/footer)

    Returns:
        Dict with markdown, title, description, url
    """
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": only_main_content,
    }

    response = requests.post(f"{BASE_URL}/scrape", headers=_headers(), json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"Firecrawl error: {data.get('error')}")

    result = data.get("data", {})
    return {
        "url": url,
        "title": result.get("metadata", {}).get("title"),
        "description": result.get("metadata", {}).get("description"),
        "markdown": result.get("markdown", ""),
    }


def search_and_scrape(query: str, limit: int = 3) -> list[dict]:
    """
    Search pages and fetch their full content.

    Args:
        query: Search query
        limit: Number of pages to fetch (default 3)

    Returns:
        List of results with full content in Markdown
    """
    results = search(query, limit=limit)
    enriched = []
    for r in results:
        try:
            scraped = scrape(r["url"])
            enriched.append({**r, **scraped})
        except Exception:
            enriched.append(r)
    return enriched


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search via Firecrawl and optionally fetch content")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, metavar="N")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--country", default="us")
    parser.add_argument("--scrape", action="store_true", help="Fetch content of each result")
    parser.add_argument("--max", type=int, default=3000, dest="max_length", metavar="N",
                        help="Maximum number of content characters (default 3000)")
    args = parser.parse_args()

    results = search(args.query, limit=args.limit, lang=args.lang, country=args.country)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.get('title', '(no title)')}")
        print(f"   URL: {r.get('url')}")
        print(f"   {r.get('description', '')[:150]}")
        print()

    if args.scrape:
        for r in results:
            print(f"\n=== {r.get('title', r.get('url'))} ===")
            print(f"URL: {r.get('url')}")
            try:
                scraped = scrape(r["url"])
                print(scraped["markdown"][:args.max_length])
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    cli()
