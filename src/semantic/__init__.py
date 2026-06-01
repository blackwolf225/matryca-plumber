"""Dual embedding: applicability synthesis, block vector store, hybrid search."""

from .applicability import ApplicabilityLLM, InstructorApplicabilityLLM, synthesize_applicability
from .config import dual_embedding_enabled, hybrid_weights
from .embedding import EmbeddingClient, OpenAICompatibleEmbeddingClient
from .indexer import index_page_blocks
from .search import format_semantic_search_markdown, hybrid_block_search
from .store import BlockVectorRecord, clear_block_vector_store_cache, load_block_vector_store

__all__ = [
    "ApplicabilityLLM",
    "BlockVectorRecord",
    "EmbeddingClient",
    "InstructorApplicabilityLLM",
    "OpenAICompatibleEmbeddingClient",
    "clear_block_vector_store_cache",
    "dual_embedding_enabled",
    "format_semantic_search_markdown",
    "hybrid_block_search",
    "hybrid_weights",
    "index_page_blocks",
    "load_block_vector_store",
    "synthesize_applicability",
]
