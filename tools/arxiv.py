"""
arXiv paper search tool.
Documentation: https://info.arxiv.org/help/api/basics.html
No API key required.
"""

import xml.etree.ElementTree as ET
import requests

BASE_URL = "https://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def search(query: str, max_results: int = 5, sort_by: str = "relevance") -> list[dict]:
    """
    Search arXiv for papers.

    Args:
        query: Search phrase. Supports field prefixes: ti: (title), au: (author),
               abs: (abstract), all: (all fields). Default: all fields.
        max_results: Number of results (default 5)
        sort_by: "relevance" or "lastUpdatedDate" or "submittedDate"

    Returns:
        List of dicts with id, title, authors, abstract, url, pdf_url, published, categories
    """
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    results = []

    for entry in root.findall("atom:entry", NS):
        arxiv_id = (entry.findtext("atom:id", "", NS) or "").split("/abs/")[-1]
        title = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
        abstract = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
        published = (entry.findtext("atom:published", "", NS) or "")[:10]

        authors = [
            a.findtext("atom:name", "", NS)
            for a in entry.findall("atom:author", NS)
        ]

        url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", NS)
        ]

        results.append({
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "url": url,
            "pdf_url": pdf_url,
            "published": published,
            "categories": categories,
        })

    return results


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search arXiv for academic papers")
    parser.add_argument("query", help="Search phrase")
    parser.add_argument("--max", type=int, default=5, dest="max_results", metavar="N",
                        help="Number of results (default 5)")
    parser.add_argument("--sort", default="relevance",
                        choices=["relevance", "lastUpdatedDate", "submittedDate"],
                        help="Sort order (default: relevance)")
    parser.add_argument("--abstract", action="store_true",
                        help="Print full abstract for each result")
    args = parser.parse_args()

    results = search(args.query, max_results=args.max_results, sort_by=args.sort)

    if not results:
        print("No results found.")
        return

    for i, r in enumerate(results, 1):
        authors_str = ", ".join(r["authors"][:3])
        if len(r["authors"]) > 3:
            authors_str += f" et al."
        print(f"{i}. {r['title']}")
        print(f"   {authors_str} ({r['published']})")
        print(f"   {r['url']}")
        if args.abstract:
            print(f"   {r['abstract'][:400]}...")
        print()


if __name__ == "__main__":
    cli()
