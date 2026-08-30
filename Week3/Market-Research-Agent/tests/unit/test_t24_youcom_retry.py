"""T24 (+): You.com client retries through two 429s then succeeds on the
third attempt."""

import httpx

from app.clients.youcom_client import YouComClient


def test_retries_through_two_429s_then_succeeds():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] < 3:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={
                "results": {
                    "web": [{"title": "Acme", "url": "https://acme.com", "description": "s"}]
                }
            },
        )

    client = YouComClient(api_key="test-key", base_url="https://ydc-index.io")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    results = client.search_web("acme competitors", category="pricing", count=5)

    assert call_count["n"] == 3
    assert len(results) == 1
    assert results[0].url == "https://acme.com"
