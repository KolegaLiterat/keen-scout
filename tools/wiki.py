"""
Wikipedia search and article retrieval tool.
Supports Polish and English. No API key required — free.
"""

import wikipedia

DEFAULT_LANG = "en"


def search(query: str, results: int = 5, lang: str = DEFAULT_LANG) -> list[str]:
    """
    Search Wikipedia for articles.

    Args:
        query: Search phrase
        results: Number of results (default 5)
        lang: Wikipedia language ('en' or 'pl')

    Returns:
        List of matching article titles
    """
    wikipedia.set_lang(lang)
    return wikipedia.search(query, results=results)


def summary(title: str, sentences: int = 5, lang: str = DEFAULT_LANG) -> dict:
    """
    Fetch a brief summary of an article.

    Args:
        title: Article title
        sentences: Number of sentences in the summary (default 5)
        lang: Wikipedia language ('en' or 'pl')

    Returns:
        Dict with title, summary, url
    """
    wikipedia.set_lang(lang)
    try:
        page = wikipedia.page(title, auto_suggest=False)
        return {
            "title": page.title,
            "summary": wikipedia.summary(title, sentences=sentences, auto_suggest=False),
            "url": page.url,
        }
    except wikipedia.DisambiguationError as e:
        # Return the first unambiguous result
        return summary(e.options[0], sentences=sentences, lang=lang)
    except wikipedia.PageError:
        # Retry with auto_suggest
        page = wikipedia.page(title, auto_suggest=True)
        return {
            "title": page.title,
            "summary": wikipedia.summary(title, sentences=sentences, auto_suggest=True),
            "url": page.url,
        }


def get_page(title: str, lang: str = DEFAULT_LANG) -> dict:
    """
    Fetch full article content.

    Args:
        title: Article title
        lang: Wikipedia language ('en' or 'pl')

    Returns:
        Dict with title, content, url, sections
    """
    wikipedia.set_lang(lang)
    try:
        page = wikipedia.page(title, auto_suggest=False)
    except wikipedia.DisambiguationError as e:
        page = wikipedia.page(e.options[0], auto_suggest=False)

    return {
        "title": page.title,
        "url": page.url,
        "content": page.content,
        "sections": page.sections,
    }


def get_section(title: str, section: str, lang: str = DEFAULT_LANG) -> str | None:
    """
    Fetch a specific section of an article.

    Args:
        title: Article title
        section: Section name
        lang: Wikipedia language

    Returns:
        Section text or None if not found
    """
    wikipedia.set_lang(lang)
    try:
        page = wikipedia.page(title, auto_suggest=False)
    except wikipedia.DisambiguationError as e:
        page = wikipedia.page(e.options[0], auto_suggest=False)

    return page.section(section)


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Search and fetch Wikipedia articles")
    parser.add_argument("query", help="Search phrase or article title")
    parser.add_argument("--lang", default="en", choices=["en", "pl"])
    parser.add_argument("--sentences", type=int, default=5, metavar="N")
    parser.add_argument("--full", action="store_true", help="Fetch full article content (not just summary)")
    parser.add_argument("--results", type=int, default=3, metavar="N", help="Number of search results")
    args = parser.parse_args()

    titles = search(args.query, results=args.results, lang=args.lang)
    print(f"Search results: {titles}\n")

    for title in titles[:2]:
        try:
            if args.full:
                page = get_page(title, lang=args.lang)
                print(f"## {page['title']}")
                print(f"URL: {page['url']}")
                print(page["content"][:5000])
            else:
                s = summary(title, sentences=args.sentences, lang=args.lang)
                print(f"## {s['title']}")
                print(f"URL: {s['url']}")
                print(s["summary"])
            print()
        except Exception as e:
            print(f"Error for '{title}': {e}\n")


if __name__ == "__main__":
    cli()
