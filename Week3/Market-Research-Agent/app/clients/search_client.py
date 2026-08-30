"""Shared interface every search-provider client implements, so
WebResearchAgent can treat You.com, Serper, or any future provider
uniformly. Not a hard runtime dependency — Python duck-typing already works
without it — but it documents the contract in one place and gives type
checkers something to check against."""

from typing import Protocol

from app.schemas.research import RawSearchResult


class SearchClientError(Exception):
    """Common base for every search-provider client's own error type
    (YouComClientError, SerperClientError, ...) so WebResearchAgent can
    catch failures from any configured provider identically."""


class SearchClient(Protocol):
    PROVIDER_NAME: str

    def search_web(self, query: str, category: str, count: int = 10) -> list[RawSearchResult]: ...

    def search_news(
        self, query: str, news_window_days: int, count: int = 10
    ) -> list[RawSearchResult]: ...
