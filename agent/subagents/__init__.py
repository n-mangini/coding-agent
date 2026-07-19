"""Subagentes del sistema multi-agente (cada uno es un `Harness` acotado)."""

from .base import Subagent
from .explorer import build_explorer
from .implementer import REPORT_FILENAME, build_implementer
from .researcher import build_researcher, extract_sources
from .reviewer import build_reviewer, extract_observations

__all__ = [
    "Subagent",
    "build_explorer",
    "build_implementer",
    "REPORT_FILENAME",
    "build_researcher",
    "extract_sources",
    "build_reviewer",
    "extract_observations",
]
