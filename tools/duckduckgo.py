"""
DuckDuckGo search tool — free, no API key required.
Based on: https://github.com/nickclyde/duckduckgo-mcp-server

Uses tools/browser.py (Playwright) for fetching page content,
which allows handling JavaScript-rendered pages.
"""

import urllib.parse
import re
import requests
from bs4 import BeautifulSoup

DDG_URL = "https://html.duckduckgo.com/html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def search(query: str, max_results: int = 10, region: str = "en-us") -> list[dict]:
    """
    Search DuckDuckGo. Free, no token limits.

    Args:
        query: Search query
        max_results: Maximum number of results (default 10)
        region: Region/language for results (default 'en-us', 'wt-wt' = no region)

    Returns:
        List of dicts with title, url, snippet, position
    """
    data = {
        "q": query,
        "b": "",
        "kl": region,
        "kp": "-1",  # SafeSearch moderate
    }

    response = requests.post(DDG_URL, data=data, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result in soup.select(".result"):
        title_elem = result.select_one(".result__title")
        if not title_elem:
            continue

        link_elem = title_elem.find("a")
        if not link_elem:
            continue

        title = link_elem.get_text(strip=True)
        link = link_elem.get("href", "")

        # Skip ads
        if "y.js" in link:
            continue

        # Clean DuckDuckGo redirect URL
        if "uddg=" in link:
            link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])

        snippet_elem = result.select_one(".result__snippet")
        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

        results.append({
            "position": len(results) + 1,
            "title": title,
            "url": link,
            "snippet": snippet,
        })

        if len(results) >= max_results:
            break

    return results


def fetch_content(url: str, use_browser: bool = False, max_length: int = 8000) -> str:
    """
    Fetch page content as plain text.

    Defaults to requests + BeautifulSoup (fast, lightweight).
    For JS-rendered pages set use_browser=True — uses Playwright.

    Args:
        url: Page URL
        use_browser: Whether to use Playwright for JS-rendered pages
        max_length: Maximum number of characters to return

    Returns:
        Plain text from the page
    """
    if use_browser:
        from tools.browser import get_page_content
        result = get_page_content(url)
        text = result["text"]
    else:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        text = " ".join(chunk for line in lines for chunk in line.split("  ") if chunk)
        text = re.sub(r"\s+", " ", text).strip()

    return text[:max_length]


def search_and_fetch(query: str, max_results: int = 3, use_browser: bool = False) -> list[dict]:
    """
    Search and fetch full content of each result.

    Args:
        query: Search query
        max_results: Number of results to fetch
        use_browser: Whether to use Playwright for fetching content

    Returns:
        List of results with full content in the 'content' field
    """
    results = search(query, max_results=max_results)
    for r in results:
        try:
            r["content"] = fetch_content(r["url"], use_browser=use_browser)
        except Exception as e:
            r["content"] = f"Error fetching content: {e}"
    return results


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search DuckDuckGo")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max", type=int, default=10, dest="max_results", metavar="N")
    parser.add_argument("--region", default="en-us")
    parser.add_argument("--fetch", action="store_true", help="Fetch content of the first 2 results")
    parser.add_argument("--browser", action="store_true", help="Use Playwright for fetching content")
    args = parser.parse_args()

    results = search(args.query, max_results=args.max_results, region=args.region)
    for r in results:
        print(f"{r['position']}. {r['title']}")
        print(f"   URL: {r['url']}")
        print(f"   {r['snippet']}")
        print()

    if args.fetch:
        for r in results[:2]:
            print(f"\n=== {r['title']} ===")
            print(f"URL: {r['url']}")
            try:
                print(fetch_content(r["url"], use_browser=args.browser))
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    cli()
