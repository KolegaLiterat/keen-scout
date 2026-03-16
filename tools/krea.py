"""
Image generation tool using Krea AI.
Models: Nano Banana 2 (default, cheaper) → Nano Banana Pro (fallback)
Documentation: https://docs.krea.ai/api-reference/image/nano-banana-2
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.krea.ai"

MODELS = {
    "nano-banana-2": "/generate/image/google/nano-banana-flash",
    "nano-banana-pro": "/generate/image/google/nano-banana-pro",
}

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9", "4:5", "5:4"]


def _headers() -> dict:
    api_key = os.getenv("KREA_API_KEY")
    if not api_key:
        raise ValueError("KREA_API_KEY not found in environment variables")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _submit_job(model: str, payload: dict) -> str:
    """Submit a job and return the job_id."""
    endpoint = MODELS[model]
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["job_id"]


def _wait_for_job(job_id: str, poll_interval: int = 5, timeout: int = 180) -> dict:
    """Poll until the job completes and return the result."""
    start = time.time()
    while time.time() - start < timeout:
        response = requests.get(
            f"{BASE_URL}/jobs/{job_id}",
            headers=_headers(),
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        if data["status"] == "completed":
            return data
        if data["status"] in ("failed", "cancelled"):
            raise RuntimeError(f"Job {job_id} ended with status: {data['status']}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    resolution: str = "1K",
    batch_size: int = 1,
    image_urls: list[str] = None,
) -> list[str]:
    """
    Generate an image from a text description.
    Uses Nano Banana 2, falls back to Nano Banana Pro on failure.

    Args:
        prompt: Image description in English
        aspect_ratio: Ratio: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 4:5, 5:4
        resolution: Resolution: 1K, 2K, 4K
        batch_size: Number of images (1–4)
        image_urls: Optional reference images (URLs)

    Returns:
        List of generated image URLs
    """
    payload = {
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "resolution": resolution,
        "batchSize": batch_size,
    }
    if image_urls:
        payload["imageUrls"] = image_urls

    for model in ("nano-banana-2", "nano-banana-pro"):
        try:
            job_id = _submit_job(model, payload)
            result = _wait_for_job(job_id)
            return result["result"]["urls"]
        except Exception as e:
            if model == "nano-banana-pro":
                raise
            print(f"[krea] {model} failed ({e}), trying nano-banana-pro...")

    return []


def generate_infographic(
    title: str,
    data_description: str,
    style: str = "clean, modern infographic, white background, data visualization",
    aspect_ratio: str = "16:9",
) -> list[str]:
    """
    Generate an infographic from a title and data description.

    Args:
        title: Infographic title
        data_description: Description of the data/content to visualize
        style: Visual style
        aspect_ratio: Aspect ratio (default 16:9)

    Returns:
        List of generated image URLs
    """
    prompt = (
        f"Infographic titled '{title}'. "
        f"Content: {data_description}. "
        f"Style: {style}. "
        f"Include clear typography, icons, and data visualizations."
    )
    return generate_image(prompt, aspect_ratio=aspect_ratio)


if __name__ == "__main__":
    print("=== Generating image: mountain landscape at sunrise ===")
    urls = generate_image(
        prompt="Sunrise over mountain peaks, golden hour, dramatic sky, photorealistic",
        aspect_ratio="16:9",
        resolution="1K",
    )
    print("Done! URLs:")
    for url in urls:
        print(f"  {url}")

    print("\n=== Generating infographic ===")
    urls2 = generate_infographic(
        title="Renewable Energy Growth 2020–2024",
        data_description="Solar: +45%, Wind: +32%, Hydro: +8%. Total renewables share grew from 28% to 38%.",
    )
    print("Done! URLs:")
    for url in urls2:
        print(f"  {url}")
