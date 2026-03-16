"""
Polona digital library search tool (National Library of Poland).
API documentation: https://polona.pl/static/polona/search-api
"""

import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://polona.pl/api/search-service"
SSL_VERIFY = False  # polona.pl has an issue with its certificate chain

SORT_OPTIONS = {
    "relevance": "RELEVANCE",
    "title_az": "TITLE_AZ",
    "title_za": "TITLE_ZA",
    "oldest": "OLDEST",
    "newest": "NEWEST",
    "recently_added": "RECENTLY_ADDED",
}


def _parse_hit(hit: dict) -> dict:
    """Flatten a hit's nested structure into a readable dict."""
    basic = hit.get("basicFields", {})
    expanded = hit.get("expandedFields", {})
    all_fields = {**basic, **expanded}

    def val(field):
        return all_fields.get(field, {}).get("values", [None])[0]

    return {
        "id": hit.get("id"),
        "title": val("title"),
        "creator": val("creator"),
        "date": val("dateDescriptive"),
        "category": val("category"),
        "language": val("language"),
        "publish_place": val("publishPlace"),
        "publisher": val("publisher"),
        "keywords": all_fields.get("keywords", {}).get("values", []),
        "url": f"https://polona.pl/item/{hit.get('id')}" if hit.get("id") else None,
        "thumbnail": hit.get("images", {}).get("thumb"),
    }


def search(
    query: str,
    page: int = 0,
    page_size: int = 10,
    sort: str = "relevance",
    only_free: bool = True,
    date_from: str = None,
    date_to: str = None,
    keywords: list[str] = None,
) -> dict:
    """
    Search Polona (simple search).

    Args:
        query: Search phrase (supports quotes, *, operator -)
        page: Page number (starting from 0)
        page_size: Results per page
        sort: Sorting: relevance, title_az, title_za, oldest, newest, recently_added
        only_free: Only objects available online without restrictions (default True)
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        keywords: List of keywords for filtering

    Returns:
        Dict with results and metadata
    """
    body = {"keywordFilters": {}}

    if only_free:
        body["keywordFilters"]["copyright"] = ["false"]

    if keywords:
        body["keywordFilters"]["keywords"] = keywords

    if date_from or date_to:
        body["temporalFilters"] = {
            "dates": {
                "startRange": date_from or "0001-01-01",
                "endRange": date_to or "9999-12-31",
            }
        }

    params = {
        "query": query,
        "page": page,
        "pageSize": page_size,
        "sort": SORT_OPTIONS.get(sort, "RELEVANCE"),
    }

    response = requests.post(
        f"{BASE_URL}/search/simple",
        params=params,
        json=body,
        timeout=15,
        verify=SSL_VERIFY,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "total": data.get("totalElements", 0),
        "page": data.get("number", 0),
        "total_pages": data.get("totalPages", 0),
        "results": [_parse_hit(h) for h in data.get("hits", [])],
    }


def search_advanced(
    page: int = 0,
    page_size: int = 10,
    sort: str = "relevance",
    only_free: bool = True,
    title: str = None,
    creator: str = None,
    keywords: str = None,
    publish_place: str = None,
    date_from: str = None,
    date_to: str = None,
) -> dict:
    """
    Search Polona (advanced search).

    Args:
        title: Title (supports AND, OR, *, -)
        creator: Author
        keywords: Keywords
        publish_place: Place of publication
        date_from / date_to: Date range (YYYY-MM-DD)

    Returns:
        Dict with results and metadata
    """
    field_queries = {}

    for field_name, value in [
        ("title", title),
        ("creator", creator),
        ("keywords", keywords),
        ("publishPlace", publish_place),
    ]:
        if value:
            field_queries[field_name] = [{"isExact": False, "query": value}]

    body = {
        "fieldQueries": field_queries,
        "filters": {
            "keywordFilters": {"copyright": ["false"]} if only_free else {},
        },
    }

    if date_from or date_to:
        body["filters"]["temporalFilters"] = {
            "dates": {
                "startRange": date_from or "0001-01-01",
                "endRange": date_to or "9999-12-31",
            }
        }

    params = {
        "page": page,
        "pageSize": page_size,
        "sort": SORT_OPTIONS.get(sort, "RELEVANCE"),
    }

    response = requests.post(
        f"{BASE_URL}/search/advanced",
        params=params,
        json=body,
        timeout=15,
        verify=SSL_VERIFY,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "total": data.get("totalElements", 0),
        "page": data.get("number", 0),
        "total_pages": data.get("totalPages", 0),
        "results": [_parse_hit(h) for h in data.get("hits", [])],
    }


def fulltext_search(query: str, page: int = 0, page_size: int = 10, only_free: bool = True) -> dict:
    """
    Full-text search — searches document content, not just metadata.

    Args:
        query: Phrase (supports quotes, *, -)
        page: Page number (starting from 0)
        page_size: Number of results
        only_free: Only objects available online

    Returns:
        Dict with results
    """
    body = {}
    if only_free:
        body["filters"] = {"keywordFilters": {"copyright": ["false"]}, "temporalFilters": None}

    response = requests.post(
        f"{BASE_URL}/fulltext/polona/fulltext/{page}/{page_size}",
        params={"sort": "RELEVANCE", "query": query},
        json=body,
        timeout=15,
        verify=SSL_VERIFY,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "total": data.get("totalElements", 0),
        "page": data.get("number", 0),
        "total_pages": data.get("totalPages", 0),
        "results": [_parse_hit(h) for h in data.get("hits", [])],
    }


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search Polona (National Library of Poland)")
    parser.add_argument("query", help="Search phrase")
    parser.add_argument("--size", type=int, default=10, dest="page_size", metavar="N")
    parser.add_argument("--sort", default="relevance",
                        choices=["relevance", "oldest", "newest", "title_az", "title_za", "recently_added"])
    parser.add_argument("--date-from", dest="date_from", metavar="YYYY-MM-DD")
    parser.add_argument("--date-to", dest="date_to", metavar="YYYY-MM-DD")
    parser.add_argument("--fulltext", action="store_true", help="Full-text search")
    args = parser.parse_args()

    if args.fulltext:
        results = fulltext_search(args.query, page_size=args.page_size)
    else:
        results = search(args.query, page_size=args.page_size, sort=args.sort,
                         date_from=args.date_from, date_to=args.date_to)

    print(f"Found: {results['total']} objects (page {results['page']+1}/{results['total_pages']})\n")
    for r in results["results"]:
        print(f"[{r['date']}] {r['title']} — {r['creator']}")
        print(f"  Category: {r['category']} | Language: {r['language']}")
        print(f"  URL: {r['url']}")
        print()


if __name__ == "__main__":
    cli()
