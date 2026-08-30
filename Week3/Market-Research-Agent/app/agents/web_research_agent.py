"""LLM-free-ish agent: mostly plain orchestration of search-provider calls,
dedup, chunking, and embedding. One instance per approved competitor.

Queries every configured search client (You.com always; Serper too, if
SERPER_ENABLED and a key is configured — see research_analysis_graph.py's
build_search_clients()) per category, merges results before dedup, so
'2+ independent sources' can genuinely mean 2 different search engines
rather than 2 results from the same one."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.clients.openai_client import get_embeddings_model
from app.clients.pinecone_client import PineconeClient
from app.clients.search_client import SearchClient, SearchClientError
from app.config import Settings
from app.prompts.web_research_prompts import build_category_query, build_news_query
from app.schemas.research import (
    NEWS_CATEGORY,
    RESEARCH_CATEGORIES,
    RawSearchResult,
    WebResearchResult,
)
from app.services import evidence_service
from app.utils.text_splitting import split_document

RESULTS_PER_CATEGORY = 5


def _pick_text(result: RawSearchResult) -> str:
    if result.highlights:
        return " ".join(result.highlights)
    if result.snippet:
        return result.snippet
    return result.title or ""


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class WebResearchAgent:
    def __init__(
        self,
        settings: Settings,
        search_clients: list[SearchClient],
        pinecone_client: PineconeClient,
    ):
        if not search_clients:
            raise ValueError("WebResearchAgent needs at least one search client")
        self._settings = settings
        self._search_clients = search_clients
        self._pinecone = pinecone_client
        self._embeddings = get_embeddings_model(settings)

    @property
    def provider_names(self) -> list[str]:
        """Used for cost recording — one run_costs row per active provider,
        since every configured client is called once per category."""
        return [client.PROVIDER_NAME for client in self._search_clients]

    def research(
        self,
        db: Session,
        run_id: UUID,
        workspace_id: str,
        competitor_id: UUID,
        competitor_name: str,
        news_window_days: int,
        categories: list[str] | None = None,
    ) -> WebResearchResult:
        categories = categories or (RESEARCH_CATEGORIES + [NEWS_CATEGORY])
        web_categories = [c for c in categories if c != NEWS_CATEGORY]
        include_news = NEWS_CATEGORY in categories

        evidence_ids: list[str] = []
        categories_covered: set[str] = set()
        warnings: list[str] = []
        failures: list[str] = []
        total_attempts = (len(web_categories) + (1 if include_news else 0)) * len(
            self._search_clients
        )

        for category in web_categories:
            query = build_category_query(competitor_name, category)
            combined_results: list[RawSearchResult] = []
            for client in self._search_clients:
                try:
                    combined_results.extend(
                        client.search_web(query, category, count=RESULTS_PER_CATEGORY)
                    )
                except SearchClientError as exc:
                    failures.append(f"{category} ({type(client).__name__}): {exc}")
            self._ingest_results(
                db,
                run_id,
                workspace_id,
                competitor_id,
                category,
                query,
                combined_results,
                evidence_ids,
                categories_covered,
                warnings,
            )

        if include_news:
            news_query = build_news_query(competitor_name)
            combined_news: list[RawSearchResult] = []
            for client in self._search_clients:
                try:
                    combined_news.extend(
                        client.search_news(news_query, news_window_days, count=RESULTS_PER_CATEGORY)
                    )
                except SearchClientError as exc:
                    failures.append(f"{NEWS_CATEGORY} ({type(client).__name__}): {exc}")
            self._ingest_results(
                db,
                run_id,
                workspace_id,
                competitor_id,
                NEWS_CATEGORY,
                news_query,
                combined_news,
                evidence_ids,
                categories_covered,
                warnings,
            )

        return WebResearchResult(
            competitor_id=str(competitor_id),
            evidence_ids=evidence_ids,
            categories_covered=sorted(categories_covered),
            warnings=warnings,
            failures=failures,
            failed=total_attempts > 0 and len(failures) == total_attempts,
        )

    def _ingest_results(
        self,
        db: Session,
        run_id: UUID,
        workspace_id: str,
        competitor_id: UUID,
        category: str,
        query: str,
        raw_results: list[RawSearchResult],
        evidence_ids: list[str],
        categories_covered: set[str],
        warnings: list[str],
    ) -> None:
        for result in raw_results:
            text = _pick_text(result)
            if not text.strip():
                continue

            evidence_id, _is_new, needs_embedding = evidence_service.record_evidence(
                db=db,
                run_id=run_id,
                competitor_id=competitor_id,
                source_type=result.source_type,
                url=result.url,
                category=category,
                query_used=query,
                evidence_text=text,
                title=result.title,
                published_at=_parse_published_at(result.published_at),
                provider=result.provider,
            )

            if needs_embedding:
                try:
                    chunk_count = self._embed_and_upsert(
                        workspace_id, run_id, competitor_id, evidence_id, category, result, text
                    )
                except Exception:  # noqa: BLE001 — never let embedding failure crash the run
                    evidence_service.update_embedding_status(db, evidence_id, "failed", 0)
                    warnings.append(f"embedding_storage_failed:{evidence_id}")
                    continue
                evidence_service.update_embedding_status(db, evidence_id, "stored", chunk_count)

            evidence_ids.append(str(evidence_id))
            categories_covered.add(category)

    def _embed_and_upsert(
        self,
        workspace_id: str,
        run_id: UUID,
        competitor_id: UUID,
        evidence_id: UUID,
        category: str,
        result: RawSearchResult,
        text: str,
    ) -> int:
        document = Document(page_content=text, metadata={"category": category})
        chunks = split_document(document)
        if not chunks:
            return 0

        vectors_text = [c.page_content for c in chunks]
        embeddings = self._embeddings.embed_documents(vectors_text)

        published_at = _parse_published_at(result.published_at)
        vectors: list[tuple[str, list[float], dict[str, Any]]] = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            metadata = {
                "workspace_id": str(workspace_id),
                "run_id": str(run_id),
                "competitor_id": str(competitor_id),
                "evidence_id": str(evidence_id),
                "category": category,
                "source_type": result.source_type,
                "canonical_url": result.url,
                "title": result.title or "",
                "published_at": published_at.isoformat() if published_at else "",
                "fetched_at": datetime.now(UTC).isoformat(),
                "chunk_index": i,
                "provider": result.provider,
                "text": chunk.page_content,
            }
            vectors.append((f"{evidence_id}_{i}", vector, metadata))

        self._pinecone.upsert(vectors, namespace=str(workspace_id))
        return len(vectors)
