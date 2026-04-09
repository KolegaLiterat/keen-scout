"""
Web search and scraping tool using Firecrawl API.
Documentation: https://docs.firecrawl.dev/features/search
             https://docs.firecrawl.dev/features/agent
"""

import os
import time
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


def agent_search(
    prompt: str,
    urls: list[str] | None = None,
    schema: dict | None = None,
    model: str = "spark-1-mini",
    max_credits: int = 500,
    poll_interval: float = 3.0,
    timeout: int = 120,
) -> dict:
    """
    Autonomous research agent — searches and gathers data from multiple sources.
    Documentation: https://docs.firecrawl.dev/features/agent

    Args:
        prompt: Natural language description of the data to collect
        urls: Optional list of URLs to search within
        schema: Optional JSON Schema dict for structured output
        model: "spark-1-mini" (faster, cheaper) or "spark-1-pro" (complex analysis)
        max_credits: Credit limit for this request (default 500)
        poll_interval: Seconds between status polls
        timeout: Maximum seconds to wait

    Returns:
        Dict with final_answer, sources, structured (if schema provided), and raw data
    """
    payload: dict = {
        "prompt": prompt,
        "model": model,
        "maxCredits": max_credits,
    }
    if urls:
        payload["urls"] = urls
    if schema:
        payload["schema"] = schema

    response = requests.post(f"{BASE_URL}/agent", headers=_headers(), json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"Firecrawl agent error: {data.get('error')}")

    job_id = data.get("jobId") or data.get("id")

    # Synchronous response (no job id) — return immediately
    if not job_id:
        result = data.get("data", data)
        return {
            "final_answer": result.get("finalAnswer") or result.get("final_answer", ""),
            "sources": result.get("sources", []),
            "structured": result.get("structuredData") or result.get("structured"),
            "data": result,
        }

    # Async — poll until complete
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(poll_interval)
        poll = requests.get(f"{BASE_URL}/agent/{job_id}", headers=_headers(), timeout=30)
        poll.raise_for_status()
        poll_data = poll.json()

        status = poll_data.get("status", "")
        if status in ("completed", "done", "success", ""):
            result = poll_data.get("data", poll_data)
            return {
                "final_answer": result.get("finalAnswer") or result.get("final_answer", ""),
                "sources": result.get("sources", []),
                "structured": result.get("structuredData") or result.get("structured"),
                "data": result,
            }
        if status in ("failed", "error"):
            raise RuntimeError(f"Firecrawl agent failed: {poll_data.get('error')}")

    raise TimeoutError(f"Firecrawl agent timed out after {timeout}s (job: {job_id})")


def agent_cli():
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Firecrawl autonomous research agent")
    parser.add_argument("prompt", help="Research prompt / question")
    parser.add_argument("--urls", nargs="+", metavar="URL", help="Optional seed URLs")
    parser.add_argument("--schema", metavar="JSON",
                        help="JSON Schema string for structured output (e.g. '{\"properties\":{...}}')")
    parser.add_argument("--model", default="spark-1-mini",
                        choices=["spark-1-mini", "spark-1-pro"],
                        help="Agent model (default: spark-1-mini)")
    parser.add_argument("--max-credits", type=int, default=500, dest="max_credits",
                        help="Credit limit (default 500)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Max seconds to wait (default 120)")
    parser.add_argument("--max", type=int, default=5000, dest="max_length",
                        help="Max characters of final_answer to print (default 5000)")
    args = parser.parse_args()

    schema = json.loads(args.schema) if args.schema else None

    result = agent_search(
        prompt=args.prompt,
        urls=args.urls,
        schema=schema,
        model=args.model,
        max_credits=args.max_credits,
        timeout=args.timeout,
    )

    print(result["final_answer"][:args.max_length])

    if result.get("structured"):
        print("\n--- Structured data ---")
        print(json.dumps(result["structured"], indent=2, ensure_ascii=False))

    if result["sources"]:
        print("\n--- Sources ---")
        for s in result["sources"]:
            if isinstance(s, dict):
                print(f"  {s.get('title', '')}  {s.get('url', s)}")
            else:
                print(f"  {s}")


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
