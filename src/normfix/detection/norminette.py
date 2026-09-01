from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from normfix.core.models import Diagnostic, Severity, SourceFile, SourceLocation


_DIAGNOSTIC = re.compile(
    r"^Error:\s+(?P<rule>[A-Z0-9_]+)\s+"
    r"\(line:\s*(?P<line>\d+),\s*col:\s*(?P<col>\d+)\):\s*"
    r"(?P<message>.*)$"
)


class NorminetteError(RuntimeError):
    pass


def _resolve_norminette() -> list[str]:
    """Return the command prefix used to invoke norminette."""
    if shutil.which("norminette"):
        return ["norminette"]
    return [sys.executable, "-m", "norminette"]


class NorminetteProvider:
    """Adapter around the installed norminette executable."""

    def __init__(self, executable: str | None = None) -> None:
        self._cmd = _resolve_norminette() if executable is None else [executable]

    def analyze(self, source: SourceFile) -> list[Diagnostic]:
        process = subprocess.run(
            self._cmd + [str(source.path)],
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode not in (0, 1):
            message = process.stderr.strip() or "norminette failed"
            raise NorminetteError(message)

        return self._parse(process.stdout, source.path)

    @staticmethod
    def _parse(output: str, path: Path) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            match = _DIAGNOSTIC.match(line)
            if not match:
                continue
            diagnostics.append(
                Diagnostic(
                    rule=match.group("rule"),
                    location=SourceLocation(
                        int(match.group("line")),
                        int(match.group("col")),
                    ),
                    message=match.group("message").strip(),
                    file=path,
                    severity=Severity.ERROR,
                )
            )
        return diagnostics
