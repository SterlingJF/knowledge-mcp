# File: server/app/types/url.py

from urllib.parse import urlparse


def validate_http_https_url(v: str) -> str:
    parsed = urlparse(v)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        msg = 'URL scheme must be http or https'
        raise ValueError(msg)
    return v
