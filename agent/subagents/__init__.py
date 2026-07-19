"""Subagentes del sistema multi-agente (cada uno es un `Harness` acotado)."""

from .base import Subagent
from .explorer import build_explorer
from .researcher import build_researcher, extract_sources

__all__ = ["Subagent", "build_explorer", "build_researcher", "extract_sources"]
