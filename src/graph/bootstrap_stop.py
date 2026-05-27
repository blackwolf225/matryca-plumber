"""Cooperative shutdown signals for Phase 1 bootstrap harvest."""


class BootstrapHarvestStopped(Exception):
    """Raised when the operator requests shutdown during catalog harvest."""


__all__ = ["BootstrapHarvestStopped"]
