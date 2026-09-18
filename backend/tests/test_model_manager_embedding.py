"""
SIH26117 — Phase 5 ModelManager Embedding Integration Tests
Verifies:
- Embedding provider selection (explicit, ModelManager, or fallback)
- ModelManager ownership over embedding delegation
- CPU embedding execution without GPU VRAM residency eviction
- Serial generation model lifecycle preservation during embedding
- Concurrent embedding and generation execution without deadlock
- Backend provider failure propagation
- Embedding vector dimension mismatch handling
- Sovereign loopback enforcement on Ollama adapters
"""

import asyncio
from pathlib import Path
import pytest
from app.services.model_manager.base import ModelInfo, ModelCapabilities
from app.services.model_manager.config_loader import ModelEntry, TierConfig, ModelTiersConfig
from app.services.model_manager.manager import ModelManager
from app.services.model_manager.mock_adapter import MockInferenceBackend
from app.services.model_manager.ollama_adapter import OllamaAdapter
from app.services.rag.base import EmbeddingModelUnavailableError, DocumentChunk
from app.services.rag.embeddings import (
    MockEmbeddingProvider,
    ModelManagerEmbeddingProvider,
    OllamaEmbeddingProvider,
)
from app.services.rag.retriever import SovereignRetriever
from app.services.rag.vector_store import LocalJsonVectorStore


def _build_test_manager(backend=None) -> ModelManager:
    """Construct a ModelManager configured for testing with an embedding role."""
    tier = TierConfig(
        description="Test Hardware Profile",
        vram_budget_gb=8.0,
        max_concurrent_models=1,
        swap_keep_alive="0m",
        reasoning=ModelEntry(provider="mock", model_tag="mock-deepseek-r1:7b"),
        vision=ModelEntry(provider="mock", model_tag="mock-qwen-vl:3b"),
        embedding=ModelEntry(provider="local", model_tag="nomic-embed-text", device="cpu"),
    )
    b = backend or MockInferenceBackend()
    return ModelManager(backend=b, tier_config=tier)


@pytest.mark.asyncio
async def test_embedding_provider_selection():
    """Retriever correctly selects ModelManagerEmbeddingProvider when ModelManager is passed."""
    mm = _build_test_manager()
    store = LocalJsonVectorStore(index_id="test_selection", auto_load=False)
    
    # 1. With ModelManager provided
    retriever_mm = SovereignRetriever(vector_store=store, model_manager=mm)
    assert isinstance(retriever_mm.embedding_provider, ModelManagerEmbeddingProvider)
    assert retriever_mm.embedding_provider.dimension() == 768

    # 2. With explicit provider provided (overrides model_manager)
    explicit_prov = MockEmbeddingProvider(dim=384)
    retriever_exp = SovereignRetriever(vector_store=store, embedding_provider=explicit_prov, model_manager=mm)
    assert retriever_exp.embedding_provider is explicit_prov

    # 3. Without model_manager or explicit provider, falls back to mock/ollama based on store dim
    retriever_fallback = SovereignRetriever(vector_store=store)
    assert isinstance(retriever_fallback.embedding_provider, (MockEmbeddingProvider, OllamaEmbeddingProvider))


@pytest.mark.asyncio
async def test_model_manager_ownership_and_delegation():
    """ModelManager delegates embedding calls to the underlying backend for 'embedding' role."""
    backend = MockInferenceBackend()
    mm = _build_test_manager(backend=backend)
    provider = ModelManagerEmbeddingProvider(model_manager=mm, dim=768)

    assert provider.is_available() is True
    assert provider.model_name() == "nomic-embed-text"

    vecs = await provider.embed_texts(["corrosion rate inspection", "minimum wall thickness"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 768
    assert len(vecs[1]) == 768

    # Test single text embedding
    single_vec = await provider.embed_text("distillation column")
    assert len(single_vec) == 768


@pytest.mark.asyncio
async def test_cpu_embedding_preserves_gpu_residency_and_lifecycle():
    """
    CRITICAL: Running embedding on CPU must NOT unload the active GPU generation model
    and must not alter the active GPU role or model tag.
    """
    backend = MockInferenceBackend()
    mm = _build_test_manager(backend=backend)

    # 1. Make reasoning model resident in VRAM
    res_gen = await mm.generate(role="reasoning", prompt="Calculate corrosion rate")
    assert "mock-deepseek-r1:7b" in res_gen
    assert mm.active_role == "reasoning"
    assert mm.active_model_tag == "mock-deepseek-r1:7b"
    assert "mock-deepseek-r1:7b" in backend.loaded_models

    # 2. Execute CPU embedding
    vecs = await mm.embed("embedding", ["test clause text"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 768

    # 3. Verify reasoning model is STILL resident and was NOT evicted
    assert mm.active_role == "reasoning"
    assert mm.active_model_tag == "mock-deepseek-r1:7b"
    assert "mock-deepseek-r1:7b" in backend.loaded_models
    assert "mock-deepseek-r1:7b" not in backend.unloaded_history


@pytest.mark.asyncio
async def test_concurrent_embedding_and_generation_no_deadlock():
    """
    Concurrent generation and CPU embedding must run safely without deadlock
    even when max_concurrent_models == 1.
    """
    backend = MockInferenceBackend()
    mm = _build_test_manager(backend=backend)

    # Launch generation and embedding concurrently
    async def run_gen():
        return await mm.generate(role="reasoning", prompt="Heavy task")

    async def run_emb():
        return await mm.embed(role="embedding", texts=["SOP Clause 4.2"])

    gen_res, emb_res = await asyncio.gather(run_gen(), run_emb())
    assert "mock-deepseek-r1:7b" in gen_res
    assert len(emb_res) == 1
    assert len(emb_res[0]) == 768


@pytest.mark.asyncio
async def test_provider_failure_propagation():
    """If backend fails during embedding, ModelManagerEmbeddingProvider propagates clean failure."""
    class FailingBackend(MockInferenceBackend):
        async def embed(self, model_id: str, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("Backend connection refused on 127.0.0.1:11434")

    mm = _build_test_manager(backend=FailingBackend())
    provider = ModelManagerEmbeddingProvider(model_manager=mm, dim=768)

    with pytest.raises(EmbeddingModelUnavailableError) as exc_info:
        await provider.embed_text("test query")
    assert "ModelManager embedding generation failed" in str(exc_info.value)
    assert "Backend connection refused" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dimension_mismatch_detection():
    """If backend returns wrong vector dimension, ModelManagerEmbeddingProvider raises dimension mismatch."""
    class WrongDimBackend(MockInferenceBackend):
        async def embed(self, model_id: str, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 512 for _ in texts]

    mm = _build_test_manager(backend=WrongDimBackend())
    provider = ModelManagerEmbeddingProvider(model_manager=mm, dim=768)

    with pytest.raises(EmbeddingModelUnavailableError) as exc_info:
        await provider.embed_text("test query")
    assert "dimension mismatch: expected 768, got 512" in str(exc_info.value)


def test_loopback_enforcement():
    """Ollama adapters must reject external or non-loopback host endpoints."""
    # OllamaEmbeddingProvider
    with pytest.raises(ValueError) as exc1:
        OllamaEmbeddingProvider(base_url="https://api.openai.com/v1")
    assert "points outside loopback" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        OllamaEmbeddingProvider(base_url="http://192.168.1.50:11434")
    assert "points outside loopback" in str(exc2.value)

    # Valid loopback URLs must be accepted
    prov_local = OllamaEmbeddingProvider(base_url="http://127.0.0.1:11434")
    assert prov_local._base_url == "http://127.0.0.1:11434"

    # OllamaAdapter
    with pytest.raises(ValueError) as exc3:
        OllamaAdapter(base_url="http://evil-cloud.com:11434")
    assert "points outside loopback" in str(exc3.value)
