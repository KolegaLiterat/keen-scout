"""
Chart and visualization tool using the Datawrapper API.
Documentation: https://developer.datawrapper.de/reference/introduction
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.datawrapper.de/v3"

CHART_TYPES = {
    "bar": "d3-bars",
    "bar-stacked": "d3-bars-stacked",
    "line": "d3-lines",
    "area": "d3-area",
    "pie": "d3-pies",
    "donut": "d3-donuts",
    "scatter": "d3-scatter-plot",
    "map": "d3-maps-choropleth",
    "table": "tables",
}


def _headers() -> dict:
    api_key = os.getenv("DATAWRAPPER_API_KEY")
    if not api_key:
        raise ValueError("DATAWRAPPER_API_KEY not found in environment variables")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_chart(
    title: str,
    chart_type: str = "bar",
    data: str = None,
    source_name: str = "",
    source_url: str = "",
    intro: str = "",
) -> dict:
    """
    Create a new chart in Datawrapper.

    Args:
        title: Chart title
        chart_type: Chart type: bar, bar-stacked, line, area, pie, donut, scatter, table
        data: CSV data (optional, can be added later via upload_data)
        source_name: Data source name
        source_url: Data source URL
        intro: Description/intro below the title

    Returns:
        Dict with chart id and edit link
    """
    dw_type = CHART_TYPES.get(chart_type, chart_type)

    payload = {
        "title": title,
        "type": dw_type,
        "metadata": {
            "describe": {
                "source-name": source_name,
                "source-url": source_url,
                "intro": intro,
            }
        },
    }

    response = requests.post(f"{BASE_URL}/charts", headers=_headers(), json=payload, timeout=15)
    response.raise_for_status()
    chart = response.json()

    chart_id = chart["id"]

    if data:
        upload_data(chart_id, data)

    return {
        "id": chart_id,
        "title": chart["title"],
        "type": chart["type"],
        "edit_url": f"https://app.datawrapper.de/chart/{chart_id}/edit",
    }


def upload_data(chart_id: str, csv_data: str) -> bool:
    """
    Upload CSV data to an existing chart.

    Args:
        chart_id: Chart ID
        csv_data: Data in CSV format (headers + rows)

    Returns:
        True on success
    """
    headers = _headers()
    headers["Content-Type"] = "text/csv"

    response = requests.put(
        f"{BASE_URL}/charts/{chart_id}/data",
        headers=headers,
        data=csv_data.encode("utf-8"),
        timeout=15,
    )
    response.raise_for_status()
    return True


def publish_chart(chart_id: str) -> dict:
    """
    Publish a chart and get the public link.

    Args:
        chart_id: Chart ID

    Returns:
        Dict with public URL and embed code
    """
    response = requests.post(
        f"{BASE_URL}/charts/{chart_id}/publish",
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    public_url = data.get("data", {}).get("publicUrl") or f"https://datawrapper.dwcdn.net/{chart_id}/"

    return {
        "id": chart_id,
        "public_url": public_url,
        "embed_code": f'<iframe title="" aria-label="Chart" src="{public_url}" scrolling="no" frameborder="0"></iframe>',
    }


def update_chart_metadata(chart_id: str, title: str = None, intro: str = None, source_name: str = None, source_url: str = None) -> bool:
    """
    Update chart metadata (title, description, source).

    Args:
        chart_id: Chart ID
        title: New title (optional)
        intro: New description (optional)
        source_name: Source name (optional)
        source_url: Source URL (optional)

    Returns:
        True on success
    """
    payload = {}
    if title:
        payload["title"] = title

    metadata_describe = {}
    if intro is not None:
        metadata_describe["intro"] = intro
    if source_name is not None:
        metadata_describe["source-name"] = source_name
    if source_url is not None:
        metadata_describe["source-url"] = source_url

    if metadata_describe:
        payload["metadata"] = {"describe": metadata_describe}

    response = requests.patch(
        f"{BASE_URL}/charts/{chart_id}",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return True


def delete_chart(chart_id: str) -> bool:
    """Delete a chart."""
    response = requests.delete(f"{BASE_URL}/charts/{chart_id}", headers=_headers(), timeout=15)
    response.raise_for_status()
    return True


if __name__ == "__main__":
    csv_data = """Year,Value
2020,42
2021,58
2022,73
2023,91
2024,105"""

    print("=== Creating test chart ===")
    chart = create_chart(
        title="Dataset Growth 2020–2024",
        chart_type="bar",
        data=csv_data,
        source_name="example-opendata.gov",
        intro="Number of published open datasets over time",
    )
    print(f"Created: {chart['id']} — {chart['edit_url']}")

    print("=== Publishing ===")
    published = publish_chart(chart["id"])
    print(f"Public URL: {published['public_url']}")

    print("=== Deleting (cleanup) ===")
    delete_chart(chart["id"])
    print("Deleted.")
