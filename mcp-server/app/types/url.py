# File: mcp-server/app/types/url.py
"""Generated-model URL validator (mcp-server/app/api_models_auto.py)."""

from urllib.parse import urlparse


def validate_http_https_url(v: str) -> str:
    """Allow no scheme, HTTP, or HTTPS."""
    parsed = urlparse(v)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        msg = "URL scheme must be http or https"
        raise ValueError(msg)
    return v
