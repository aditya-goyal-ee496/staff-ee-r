"""Milvus Lite adapter for the SemanticIndex port.

Embeds scrubbed consultant skill text via SentenceTransformer and stores vectors
in a local Milvus Lite database behind the SemanticIndex port.
Lazy imports keep the module loadable when extras are absent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from staffeer.domain.errors import SemanticIndexError
from staffeer.ports.semantic_index import Hit, IndexItem

try:
    import structlog as _structlog

    _log = _structlog.get_logger(__name__)
except ImportError:  # pragma: no cover
    _log = logging.getLogger(__name__)

_COLLECTION = "consultant_skills"


class MilvusSemanticIndex:
    """Milvus Lite-backed semantic index satisfying the SemanticIndex port."""

    def __init__(self, db_path: str, model_name: str = "all-MiniLM-L6-v2") -> None:
        from pymilvus import DataType, MilvusClient  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        self._model = SentenceTransformer(model_name)
        probe: list[float] = self._model.encode("probe").tolist()
        self._dim = len(probe)
        # Milvus Lite opens (not creates) the db file's directory; make it exist first.
        Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._client: MilvusClient = MilvusClient(db_path)
        self._DataType = DataType
        self._ensure_collection()
        _log.info("milvus_index.ready", db_path=db_path, dim=self._dim)

    def _ensure_collection(self) -> None:
        if self._client.has_collection(_COLLECTION):
            return
        DataType = self._DataType
        schema = self._client.create_schema()
        schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False)
        schema.add_field("text", DataType.VARCHAR, max_length=2048)
        schema.add_field("namespace", DataType.VARCHAR, max_length=64)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=self._dim)
        schema.add_field("meta_json", DataType.VARCHAR, max_length=4096)
        # FLAT (exact, brute-force) suits the POC's small consultant pool: no training/
        # clustering step, so it is robust at any size. IVF_FLAT needs many training points
        # (nlist centroids) and is for large corpora — overkill and unstable here.
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            "embedding",
            index_type="FLAT",
            metric_type="COSINE",
        )
        self._client.create_collection(_COLLECTION, schema=schema, index_params=index_params)

    def _embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()  # type: ignore[no-any-return]

    def upsert(self, item: IndexItem) -> None:
        """Embed and persist item; idempotent on id."""
        try:
            vector = self._embed(item.text)
            self._client.delete(_COLLECTION, ids=[item.id])
            self._client.insert(
                _COLLECTION,
                [
                    {
                        "id": item.id,
                        "text": item.text[:2048],
                        "namespace": item.namespace[:64],
                        "embedding": vector,
                        "meta_json": json.dumps(item.metadata)[:4096],
                    }
                ],
            )
            _log.debug("milvus_index.upserted", id=item.id)
        except Exception as exc:
            raise SemanticIndexError(f"upsert failed for id={item.id!r}") from exc

    _NAMESPACE_RE = __import__("re").compile(r"^[A-Za-z0-9_-]{0,64}$")

    @staticmethod
    def _map_hit(hit: dict) -> Hit:  # type: ignore[type-arg]
        """Convert a raw Milvus search hit to a Hit value object."""
        entity = hit["entity"]
        metadata = json.loads(entity.get("meta_json") or "{}")
        return Hit(
            id=hit["id"],
            score=float(hit["distance"]),
            text=entity.get("text", ""),
            metadata=metadata,
        )

    def query(self, text: str, namespace: str, top_k: int) -> list[Hit]:
        """Return up to top_k nearest neighbours; empty when top_k==0 or index empty."""
        if top_k == 0:
            return []
        if namespace and not self._NAMESPACE_RE.match(namespace):
            raise SemanticIndexError("query failed: invalid namespace value")
        try:
            vector = self._embed(text)
            # Milvus requires the collection loaded into memory before search; this also
            # makes rows inserted since the last load searchable. Idempotent when loaded.
            self._client.load_collection(_COLLECTION)
            filter_expr = f'namespace == "{namespace}"' if namespace else ""
            results = self._client.search(
                _COLLECTION,
                data=[vector],
                anns_field="embedding",
                search_params={"metric_type": "COSINE"},
                limit=top_k,
                filter=filter_expr,
                output_fields=["id", "text", "meta_json"],
            )
            return [self._map_hit(h) for h in results[0]]
        except SemanticIndexError:
            raise
        except Exception as exc:
            raise SemanticIndexError("query failed") from exc
