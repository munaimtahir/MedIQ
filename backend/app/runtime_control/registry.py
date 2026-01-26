"""Module registry: map (module_key, version_key) -> implementation. Stubs only."""

from app.runtime_control.contracts import ModuleKey

# registry[module_key][version_key] -> implementation class or callable (stub)
# Implementations plug in from learning_engine, search, graph, warehouse, etc.
_registry: dict[str, dict[str, type]] = {}


def register(module_key: str, version_key: str, impl: type) -> None:
    """Register an implementation for (module_key, version_key)."""
    _registry.setdefault(module_key, {})[version_key] = impl


def get_impl(module_key: str, version_key: str) -> type | None:
    """Return registered implementation or None."""
    return (_registry.get(module_key) or {}).get(version_key)


def bridge_state(module_key: str, from_version: str, to_version: str, user_id: str) -> bool:
    """
    Idempotent state bridge between versions. No-op stub.
    Canonical stores are shared; bridge ensures compatibility when switching.
    """
    # Stub: no-op. Real impl would ensure canonical state compatible with to_version.
    return True
