"""
Open data search tool for dane.gov.pl (Polish open data portal).
API: https://api.dane.gov.pl/doc#/
"""

import requests

BASE_URL = "https://api.dane.gov.pl/1.4"


def search_datasets(query: str, page: int = 1, per_page: int = 5, category: str = None) -> dict:
    """
    Search datasets by keywords.

    Args:
        query: Search phrase
        page: Page number (default 1)
        per_page: Results per page (default 5, max 100)
        category: Category ID (optional)

    Returns:
        Dict with dataset list and metadata
    """
    params = {
        "q": query,
        "page": page,
        "per_page": per_page,
        "sort": "-verified",
    }
    if category:
        params["category"] = category

    response = requests.get(f"{BASE_URL}/datasets", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        results.append({
            "id": item["id"],
            "slug": attrs.get("slug"),
            "title": attrs.get("title"),
            "notes": _strip_html(attrs.get("notes", "")),
            "category": attrs.get("category", {}).get("title"),
            "formats": attrs.get("formats", []),
            "modified": attrs.get("modified"),
            "url": item.get("links", {}).get("self"),
        })

    return {
        "count": data.get("meta", {}).get("count", 0),
        "page": page,
        "per_page": per_page,
        "results": results,
    }


def get_dataset_resources(dataset_id: str) -> list[dict]:
    """
    Get the list of resources (files/links) for a given dataset.

    Args:
        dataset_id: Dataset ID or slug (e.g. "7" or "7,dataset-name")

    Returns:
        List of resources with download links
    """
    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}", timeout=10)
    response.raise_for_status()
    data = response.json()

    resources = []
    for rel in data.get("data", {}).get("relationships", {}).get("resources", {}).get("data", []):
        resources.append(rel)

    # Fetch resource details
    response2 = requests.get(f"{BASE_URL}/datasets/{dataset_id}/resources", timeout=10)
    response2.raise_for_status()
    res_data = response2.json()

    result = []
    for item in res_data.get("data", []):
        attrs = item.get("attributes", {})
        result.append({
            "id": item["id"],
            "title": attrs.get("title"),
            "format": attrs.get("format"),
            "file_url": attrs.get("file_url"),
            "download_url": attrs.get("download_url"),
            "modified": attrs.get("modified"),
            "description": attrs.get("description"),
        })

    return result


def fetch_resource_data(resource_id: str, rows: int = 10) -> dict:
    """
    Fetch data from a resource (if available as a table).

    Args:
        resource_id: Resource ID
        rows: Number of rows to fetch (default 10)

    Returns:
        Dict with columns and data rows
    """
    params = {"per_page": rows, "page": 1}
    response = requests.get(f"{BASE_URL}/resources/{resource_id}/data", params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    return {
        "count": data.get("meta", {}).get("count"),
        "columns": [
            col.get("name") for col in data.get("data", {}).get("attributes", {}).get("schema", {}).get("fields", [])
        ],
        "rows": data.get("data", {}).get("attributes", {}).get("data", []),
    }


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search open data from dane.gov.pl")
    parser.add_argument("query", help="Search phrase")
    parser.add_argument("--per-page", type=int, default=5, dest="per_page", metavar="N")
    parser.add_argument("--resources", action="store_true",
                        help="Also fetch resource list for the first result")
    args = parser.parse_args()

    results = search_datasets(args.query, per_page=args.per_page)
    print(f"Found: {results['count']} datasets\n")
    for r in results["results"]:
        print(f"[{r['id']}] {r['title']}")
        print(f"  Category: {r['category']} | Formats: {r['formats']}")
        print(f"  {r['notes'][:120]}" if r['notes'] else "")
        print()

    if args.resources and results["results"]:
        first = results["results"][0]
        dataset_id = f"{first['id']},{first['slug']}"
        print(f"=== Resources for: {first['title']} ===")
        resources = get_dataset_resources(dataset_id)
        for res in resources[:5]:
            print(f"  [{res['id']}] {res['title']} ({res['format']})")
            print(f"  {res['download_url']}")
            print()


if __name__ == "__main__":
    cli()
