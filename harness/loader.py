"""Dynamically load engines/<name>.py and validate the Core 3 contract."""

from __future__ import annotations

import importlib
from types import ModuleType

REQUIRED_CALLABLES = ("get_pseudo_legal_moves", "evaluate_board", "order_moves")


class EngineContractError(RuntimeError):
    pass


def load_engine(name: str) -> ModuleType:
    try:
        module = importlib.import_module(f"engines.{name}")
    except ImportError as exc:
        raise EngineContractError(
            f"Could not import engines.{name}: {exc}"
        ) from exc

    missing = [fn for fn in REQUIRED_CALLABLES if not callable(getattr(module, fn, None))]
    if missing:
        raise EngineContractError(
            f"engines/{name}.py is missing required callable(s): {', '.join(missing)}. "
            f"Each engine must expose: {', '.join(REQUIRED_CALLABLES)}."
        )
    return module
