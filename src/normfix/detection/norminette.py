from __future__ import annotations

import json
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

    def analyze_batch(
        self, paths: list[Path]
    ) -> dict[Path, list[Diagnostic]]:
        """Analyze multiple files in a single subprocess call using JSON output."""
        if not paths:
            return {}
        if len(paths) == 1:
            source = SourceFile(paths[0], paths[0].read_text(encoding="utf-8"))
            return {paths[0]: self.analyze(source)}

        process = subprocess.run(
            self._cmd + ["-f", "json"] + [str(p) for p in paths],
            text=True,
            capture_output=True,
            check=False,
        )
        if process.returncode not in (0, 1):
            message = process.stderr.strip() or "norminette failed"
            raise NorminetteError(message)

        return self._parse_json(process.stdout, paths)

    @staticmethod
    def _parse_json(
        output: str, paths: list[Path]
    ) -> dict[Path, list[Diagnostic]]:
        """Parse norminette JSON output into diagnostics keyed by path."""
        json_start = output.find("{")
        if json_start < 0:
            raise NorminetteError("No JSON in norminette output")
        data = json.loads(output[json_start:])

        path_lookup = {str(p.resolve()): p for p in paths}
        result: dict[Path, list[Diagnostic]] = {p: [] for p in paths}

        for file_entry in data.get("files", []):
            raw_path = file_entry["path"]
            resolved = str(Path(raw_path).resolve())
            path = path_lookup.get(resolved)
            if path is None:
                continue

            severity = Severity.ERROR if file_entry.get("status") == "Error" else Severity.WARNING
            for error in file_entry.get("errors", []):
                highlights = error.get("highlights", [])
                if not highlights:
                    continue
                hl = highlights[0]
                result[path].append(
                    Diagnostic(
                        rule=error["name"],
                        location=SourceLocation(hl["lineno"], hl["column"]),
                        message=error.get("text", ""),
                        file=path,
                        severity=severity,
                    )
                )
        return result

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
