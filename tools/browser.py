"""
Browser automation tool using Playwright.
Used when pages render via JavaScript (SPA) or require interaction.
"""

from playwright.sync_api import sync_playwright, Page, Browser


def get_page_content(url: str, wait_for: str = None, timeout: int = 15000) -> dict:
    """
    Fetch rendered page content (after JavaScript execution).

    Args:
        url: Page URL
        wait_for: CSS selector or text to wait for before extracting content
        timeout: Timeout in ms (default 15000)

    Returns:
        Dict with title, text (plain text), html, url
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="networkidle")

        if wait_for:
            page.wait_for_selector(wait_for, timeout=timeout)

        title = page.title()
        text = page.evaluate("() => document.body.innerText")
        html = page.content()
        final_url = page.url

        browser.close()

    return {
        "url": final_url,
        "title": title,
        "text": text,
        "html": html,
    }


def screenshot(url: str, path: str = "screenshot.png", full_page: bool = True, timeout: int = 15000) -> str:
    """
    Take a screenshot of a page.

    Args:
        url: Page URL
        path: Output file path (PNG)
        full_page: Whether to capture the full page (default True)
        timeout: Timeout in ms

    Returns:
        Path to the saved file
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, timeout=timeout, wait_until="networkidle")
        page.screenshot(path=path, full_page=full_page)
        browser.close()

    return path


def extract_links(url: str, timeout: int = 15000) -> list[dict]:
    """
    Extract all links from a page.

    Args:
        url: Page URL
        timeout: Timeout in ms

    Returns:
        List of dicts with href and text
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="networkidle")

        links = page.evaluate("""() =>
            Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({ href: a.href, text: a.innerText.trim() }))
                .filter(l => l.href.startsWith('http') && l.text.length > 0)
        """)

        browser.close()

    return links


def run_js(url: str, script: str, timeout: int = 15000):
    """
    Open a page and execute arbitrary JavaScript, return the result.

    Args:
        url: Page URL
        script: JavaScript code to execute (as arrow function, e.g. '() => document.title')
        timeout: Timeout in ms

    Returns:
        Result of the script execution
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="networkidle")
        result = page.evaluate(script)
        browser.close()

    return result


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch page content via browser (Playwright)")
    parser.add_argument("url", help="Page URL to fetch")
    parser.add_argument("--max", type=int, default=5000, dest="max_length", metavar="N",
                        help="Maximum number of characters (default 5000)")
    parser.add_argument("--timeout", type=int, default=15000, metavar="MS")
    parser.add_argument("--wait-for", dest="wait_for", metavar="SELECTOR",
                        help="CSS selector to wait for before extracting content")
    args = parser.parse_args()

    result = get_page_content(args.url, wait_for=args.wait_for, timeout=args.timeout)
    print(f"=== {result['title']} ===")
    print(f"URL: {result['url']}")
    print(result["text"][:args.max_length])


if __name__ == "__main__":
    cli()
