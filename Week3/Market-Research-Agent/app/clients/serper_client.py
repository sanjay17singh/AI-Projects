"""The only module that speaks HTTP to Serper.dev. Same search_web/search_news
shape as YouComClient — WebResearchAgent treats every configured search
client uniformly through this interface.

Built against publicly documented Serper conventions (POST
https://google.serper.dev/search and /news, header X-API-KEY, response
{"organic": [...]} / {"news": [...]}, date filtering via tbs=qdr:d{N}) —
NOT yet exercised against a live key in this codebase. Re-verify the first
time a real SERPER_API_KEY is available, the same way app/clients/youcom_client.py
was corrected after its initial endpoint-shape assumption turned out wrong."""

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


class SerperClientError(SearchClientError):
    pass


class SerperClient:
    """Second, independent search provider — see YouComClient for the
    interface this must match. Deliberately a plain Google-results proxy
    (not another AI-search aggregator) so its results are genuinely
    independent of You.com's, not just a second call to a similar index."""

    PROVIDER_NAME = "serper"

    def __init__(
        self, api_key: str, base_url: str = "https://google.serper.dev", timeout: float = 15.0
    ):
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
    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post(
            f"{self._base_url}{path}",
            headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def search_web(self, query: str, category: str, count: int = 10) -> list[RawSearchResult]:
        try:
            data = self._post("/search", {"q": query, "num": count})
        except httpx.HTTPError as exc:
            raise SerperClientError(f"Serper web search failed for {query!r}: {exc}") from exc
        return self._parse_results(
            data, section="organic", category=category, query_used=query, source_type="web"
        )

    def search_news(
        self, query: str, news_window_days: int, count: int = 10
    ) -> list[RawSearchResult]:
        try:
            data = self._post(
                "/news", {"q": query, "num": count, "tbs": f"qdr:d{news_window_days}"}
            )
        except httpx.HTTPError as exc:
            raise SerperClientError(f"Serper news search failed for {query!r}: {exc}") from exc
        return self._parse_results(
            data, section="news", category="news", query_used=query, source_type="news"
        )

    @staticmethod
    def _parse_results(
        data: dict[str, Any], section: str, category: str, query_used: str, source_type: str
    ) -> list[RawSearchResult]:
        items = data.get(section) or []
        results: list[RawSearchResult] = []
        for item in items:
            url = item.get("link")
            if not url:
                continue
            results.append(
                RawSearchResult(
                    title=item.get("title"),
                    url=url,
                    snippet=item.get("snippet"),
                    highlights=None,
                    published_at=item.get("date"),
                    category=category,
                    query_used=query_used,
                    source_type=source_type,
                    provider="serper",
                )
            )
        return results
