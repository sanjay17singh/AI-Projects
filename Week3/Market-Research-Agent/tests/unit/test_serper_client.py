"""Supplementary coverage (beyond the original 25 scenarios) for the Serper
search client added alongside You.com. Mirrors T24's retry-through-429s
pattern, plus checks the Serper-specific request/response shape: /search vs
/news endpoints, the tbs=qdr:d{N} freshness parameter, and parsing the
"organic"/"news" response sections."""

import httpx

from app.clients.serper_client import SerperClient


def test_search_web_hits_search_endpoint_and_parses_organic_results():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json={"organic": [{"title": "Acme", "link": "https://acme.com", "snippet": "s"}]},
        )

    client = SerperClient(api_key="test-key", base_url="https://google.serper.dev")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    results = client.search_web("acme pricing", category="pricing", count=5)

    assert captured["url"] == "https://google.serper.dev/search"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert len(results) == 1
    assert results[0].url == "https://acme.com"
    assert results[0].provider == "serper"
    assert results[0].category == "pricing"
    assert results[0].source_type == "web"


def test_search_news_hits_news_endpoint_with_freshness_filter():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "news": [
                    {
                        "title": "Acme raises funding",
                        "link": "https://news.example.com/acme",
                        "snippet": "s",
                        "date": "2 days ago",
                    }
                ]
            },
        )

    client = SerperClient(api_key="test-key", base_url="https://google.serper.dev")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    results = client.search_news("Acme", news_window_days=60, count=5)

    assert captured["url"] == "https://google.serper.dev/news"
    assert captured["body"]["tbs"] == "qdr:d60"
    assert len(results) == 1
    assert results[0].source_type == "news"
    assert results[0].category == "news"
    assert results[0].published_at == "2 days ago"


def test_retries_through_two_429s_then_succeeds():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] < 3:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200, json={"organic": [{"title": "Acme", "link": "https://acme.com"}]}
        )

    client = SerperClient(api_key="test-key")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    results = client.search_web("acme competitors", category="pricing", count=5)

    assert call_count["n"] == 3
    assert len(results) == 1
