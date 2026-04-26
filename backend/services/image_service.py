from __future__ import annotations

import os
from urllib.parse import quote_plus


def fetch_image(keyword: str) -> str:
    """Return a real image URL using Unsplash Source endpoint when possible."""
    cleaned = quote_plus((keyword or "presentation").strip())
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if unsplash_key:
        return f"https://api.unsplash.com/photos/random?query={cleaned}&client_id={unsplash_key}"

    # Fallback public dynamic image.
    return f"https://source.unsplash.com/featured/1280x720/?{cleaned}"
