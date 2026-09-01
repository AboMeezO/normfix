from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from normfix.core.models import Diagnostic, Edit, SourceFile


@dataclass(frozen=True)
class FixContext:
    source: SourceFile
    diagnostic: Diagnostic


class Fixer(ABC):
    id: str
    description: str
    priority: int = 100

    @abstractmethod
    def supports(self, diagnostic: Diagnostic) -> bool:
        """Return whether this fixer can handle the diagnostic."""

    def supports_rule(self, rule: str) -> bool:
        """Allow a fixer to advertise multiple Norm rule codes."""
        return self.supports(
            Diagnostic(rule=rule, location=None, message="", file=None)
        )

    @abstractmethod
    def plan(self, context: FixContext) -> list[Edit]:
        """Return source edits without modifying the source."""


class DiagnosticProvider(Protocol):
    def analyze(self, source: SourceFile) -> list[Diagnostic]:
        ...
