"""Shadow DB (`shadow.sqlite`) — daemon-owned read cache and memory graph layer."""

from .schema import (
    MEMORY_GRAPH_DDL,
    SHADOW_DDL,
    SHADOW_META_SEED,
    SHADOW_PRAGMAS,
    SHADOW_READ_DDL,
    SHADOW_SCHEMA_VERSION,
    apply_shadow_schema,
)

__all__ = [
    "MEMORY_GRAPH_DDL",
    "SHADOW_DDL",
    "SHADOW_META_SEED",
    "SHADOW_PRAGMAS",
    "SHADOW_READ_DDL",
    "SHADOW_SCHEMA_VERSION",
    "apply_shadow_schema",
]
