"""In-memory stand-in for app.clients.pinecone_client.PineconeClient — same
public interface (ensure_index/upsert/query/delete_namespace), no network."""

from typing import Any


class FakePineconeClient:
    def __init__(self):
        self.store: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}
        self.upsert_should_fail = False

    def ensure_index(self) -> None:
        pass

    def upsert(
        self, vectors: list[tuple[str, list[float], dict[str, Any]]], namespace: str
    ) -> None:
        if self.upsert_should_fail:
            raise RuntimeError("simulated Pinecone upsert failure")
        ns = self.store.setdefault(namespace, {})
        for vector_id, values, metadata in vectors:
            ns[vector_id] = (values, metadata)

    def query(
        self, vector: list[float], namespace: str, top_k: int, filter: dict[str, Any]
    ) -> list[dict[str, Any]]:
        ns = self.store.get(namespace, {})
        matches = [
            {"metadata": metadata, "score": 1.0}
            for _values, metadata in ns.values()
            if self._matches(metadata, filter)
        ]
        return matches[:top_k]

    def delete_namespace(self, namespace: str) -> None:
        self.store.pop(namespace, None)

    @staticmethod
    def _matches(metadata: dict[str, Any], filter: dict[str, Any]) -> bool:
        for key, condition in filter.items():
            value = metadata.get(key)
            if isinstance(condition, dict):
                if "$eq" in condition and value != condition["$eq"]:
                    return False
                if "$gte" in condition and (value is None or value < condition["$gte"]):
                    return False
            elif value != condition:
                return False
        return True
