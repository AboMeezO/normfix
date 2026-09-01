from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int


@dataclass(frozen=True)
class SourceFile:
    path: Path
    content: str


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    location: SourceLocation
    message: str
    file: Path
    severity: Severity = Severity.ERROR


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    replacement: str
    rule: str


@dataclass(frozen=True)
class FixResult:
    file: Path
    edits: tuple[Edit, ...]
    skipped: bool = False
    reason: str | None = None
