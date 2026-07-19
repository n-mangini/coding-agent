"""Subagentes del sistema multi-agente (cada uno es un `Harness` acotado)."""

from .base import Subagent
from .explorer import build_explorer

__all__ = ["Subagent", "build_explorer"]
