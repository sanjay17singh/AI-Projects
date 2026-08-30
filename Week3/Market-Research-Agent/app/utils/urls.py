from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAMS = {"fbclid", "gclid", "msclkid", "ref", "mc_cid", "mc_eid", "igshid"}


def canonicalize_url(url: str) -> str:
    """Normalizes a URL for dedup purposes: lowercase host, strip default port,
    strip fragment, drop tracking query params, sort remaining ones, drop a
    trailing slash on the path."""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    if netloc.endswith(":80") and parsed.scheme == "http":
        netloc = netloc[: -len(":80")]
    if netloc.endswith(":443") and parsed.scheme == "https":
        netloc = netloc[: -len(":443")]

    kept_params = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith(_TRACKING_PARAM_PREFIXES)
    ]
    kept_params.sort()
    query = urlencode(kept_params)

    path = parsed.path.rstrip("/") or "/"

    return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))
