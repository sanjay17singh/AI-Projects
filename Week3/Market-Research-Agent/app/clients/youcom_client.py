"""The only module that speaks HTTP to You.com. Every test replaces this class
with a fake implementing the same search_web/search_news interface — nothing
else in the app imports httpx or knows the request/response shape directly.

Verified against the real You.com Search API (POST https://ydc-index.io/v1/search,
header X-API-Key: <raw key>, response shape {"results": {"web": [...], "news": [...]}}
with per-item fields url/title/description/snippets/contents.highlights/page_age) —
see docs/SETUP.md's troubleshooting note if this ever needs re-checking against
the live API."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.clients.search_client import SearchClientError
from app.schemas.research import RawSearchResult


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


class YouComClientError(SearchClientError):
    pass


class YouComClient:
    """Thin wrapper around the You.com POST Search API (a single /v1/search
    endpoint returns both `results.web` and `results.news` sections; there is
    no separate news endpoint — the news call adds a `freshness` date-range
    parameter and reads the `news` section instead of `web`). Uses
    query-aware `highlights` over `snippet` when the response provides them
    (preferred for relevance, per the product requirement)."""

    PROVIDER_NAME = "you_com"

    def __init__(self, api_key: str, base_url: str, timeout: float = 15.0):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception(_is_retryable),
    )
    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post(
            f"{self._base_url}/v1/search",
            headers={"X-API-Key": self._api_key, "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def search_web(self, query: str, category: str, count: int = 10) -> list[RawSearchResult]:
        try:
            data = self._post({"query": query, "count": count})
        except httpx.HTTPError as exc:
            raise YouComClientError(f"You.com web search failed for {query!r}: {exc}") from exc
        return self._parse_results(
            data, section="web", category=category, query_used=query, source_type="web"
        )

    def search_news(
        self, query: str, news_window_days: int, count: int = 10
    ) -> list[RawSearchResult]:
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=news_window_days)
        freshness = f"{start_date.isoformat()}to{end_date.isoformat()}"
        try:
            data = self._post({"query": query, "count": count, "freshness": freshness})
        except httpx.HTTPError as exc:
            raise YouComClientError(f"You.com news search failed for {query!r}: {exc}") from exc
        return self._parse_results(
            data, section="news", category="news", query_used=query, source_type="news"
        )

    @staticmethod
    def _parse_results(
        data: dict[str, Any], section: str, category: str, query_used: str, source_type: str
    ) -> list[RawSearchResult]:
        items = (data.get("results") or {}).get(section) or []
        results: list[RawSearchResult] = []
        for item in items:
            url = item.get("url")
            if not url:
                continue
            snippets = item.get("snippets") or []
            snippet = snippets[0] if snippets else item.get("description")
            highlights = (item.get("contents") or {}).get("highlights")
            results.append(
                RawSearchResult(
                    title=item.get("title"),
                    url=url,
                    snippet=snippet,
                    highlights=highlights or None,
                    published_at=item.get("page_age"),
                    category=category,
                    query_used=query_used,
                    source_type=source_type,
                )
            )
        return results
