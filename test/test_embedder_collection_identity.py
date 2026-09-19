"""Collection identity prevents mixing equally wide, incompatible vectors."""
from unittest.mock import Mock

import pytest

from src.document_processor import ingest_corpus as ic


REAL = "all-MiniLM-L6-v2"
OFFLINE = "all-MiniLM-L6-v2-offline"


@pytest.fixture
def model(monkeypatch):
    model = Mock()
    monkeypatch.setattr(ic, "_load_embedder", lambda: (model, REAL, 384))
    return model


def test_new_collection_is_stamped_before_return(model):
    client = Mock()
    collection = Mock(metadata={"hnsw:space": "cosine", "embedder_model": REAL})
    client.get_or_create_collection.return_value = collection
    assert ic.get_or_create_collection(client) is collection
    client.get_or_create_collection.assert_called_once_with(
        name=ic.COLLECTION,
        metadata={"hnsw:space": "cosine", "embedder_model": REAL},
    )
    collection.modify.assert_not_called()


@pytest.mark.parametrize("metadata", [None, {}, {"hnsw:space": "cosine", "owner": "course"}])
def test_legacy_collection_is_adopted_without_recreating(model, metadata, caplog):
    client = Mock()
    collection = Mock(metadata=metadata)
    client.get_or_create_collection.return_value = collection
    assert ic.get_or_create_collection(client) is collection
    expected = {k: v for k, v in (metadata or {}).items() if k != "hnsw:space"}
    collection.modify.assert_called_once_with(metadata={**expected, "embedder_model": REAL})
    client.delete_collection.assert_not_called()
    assert "Adopted unstamped collection" in caplog.text


@pytest.mark.parametrize("active,stored", [(REAL, OFFLINE), (OFFLINE, REAL), (REAL, "")])
def test_different_stamp_refuses_without_mutating_collection(monkeypatch, active, stored):
    monkeypatch.setattr(ic, "_load_embedder", lambda: (Mock(), active, 384))
    client = Mock()
    collection = Mock(metadata={"embedder_model": stored})
    client.get_or_create_collection.return_value = collection
    with pytest.raises(ic.EmbedderMismatchError, match="active embedder"):
        ic.get_or_create_collection(client)
    collection.modify.assert_not_called()
    collection.query.assert_not_called()
    collection.upsert.assert_not_called()


def test_failed_adoption_does_not_return_unstamped_collection(model):
    client = Mock()
    collection = Mock(metadata={"hnsw:space": "cosine"})
    collection.modify.side_effect = RuntimeError("metadata update unavailable")
    client.get_or_create_collection.return_value = collection
    with pytest.raises(RuntimeError, match="metadata update unavailable"):
        ic.get_or_create_collection(client)


def test_api_state_does_not_hide_mismatch_with_fixture_answer(monkeypatch):
    from src.api import state as state_module
    from src.document_processor import rag_pipeline

    monkeypatch.setattr(state_module.APIState, "__post_init__", lambda self: None)
    retriever = Mock(side_effect=ic.EmbedderMismatchError("wrong model"))
    monkeypatch.setattr(rag_pipeline, "VectorRetriever", retriever)
    fallback = Mock()
    monkeypatch.setattr(state_module, "_FixtureGenerator", fallback)
    state = state_module.APIState(fixtures={})
    for _ in range(2):
        with pytest.raises(ic.EmbedderMismatchError):
            state.get_generator()
    assert state.backend_mode == "embedder_mismatch"
    assert not state.rag_available
    assert state._generator is None
    fallback.assert_not_called()


def test_indexing_mismatch_fails_job_before_embedding_or_writing(monkeypatch, tmp_path):
    from src.api.routes.documents import _bg_index_document
    from src.document_processor import chunker

    monkeypatch.setattr(chunker, "extract_and_chunk", lambda path: [{"text": "material"}])
    client = Mock()
    monkeypatch.setattr(ic, "get_chroma_client", lambda: client)
    model = Mock()
    monkeypatch.setattr(ic, "_load_embedder", lambda: (model, REAL, 384))
    collection = Mock(metadata={"embedder_model": OFFLINE})
    client.get_or_create_collection.return_value = collection
    state = Mock()
    _bg_index_document(tmp_path / "lecture.pdf", "CSIT321", "doc", "job", state)
    state.update_document_status.assert_called_with("doc", "failed")
    assert state.update_job.call_args.kwargs["status"] == "failed"
    model.encode.assert_not_called()
    collection.upsert.assert_not_called()
