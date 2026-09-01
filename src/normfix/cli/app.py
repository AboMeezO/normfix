from collections import defaultdict
from pathlib import Path

import typer
from rich.console import Console

from normfix.core.edits import apply_edits
from normfix.core.models import SourceFile
from normfix.detection.norminette import NorminetteError, NorminetteProvider
from normfix.presentation.report import print_check_report
from normfix.project.discovery import discover_files
from normfix.rules.base import FixContext
from normfix.rules.builtin import create_registry
from normfix.rules.formatting.layout import function_spans

app = typer.Typer(no_args_is_help=True, help="Safe fixer for 42 Norm violations.")
console = Console()


def _scan(path: Path) -> tuple[list[Path], dict[Path, list]]:
    provider = NorminetteProvider()
    files = discover_files(path)
    diagnostics_by_file = provider.analyze_batch(files)
    return files, diagnostics_by_file


def _header_end(source: str) -> int:
    """Return the offset after an existing 42 header, if present."""
    lines = source.splitlines(keepends=True)
    marker = "/* ************************************************************************** */"
    if not lines or lines[0].rstrip("\r\n") != marker:
        return 0
    offset = 0
    for index, line in enumerate(lines[:20]):
        offset += len(line)
        if index > 0 and line.rstrip("\r\n") == marker:
            return offset
    return 0


def _protected_edits(source: str, edits):
    end = _header_end(source)
    if not end:
        return edits
    return [edit for edit in edits if edit.start >= end]


def _apply_file(source: SourceFile, diagnostics: list, registry) -> SourceFile:
    content = source.content
    cached_spans = tuple(function_spans(content))
    for fixer in registry.all():
        matching = [d for d in diagnostics if fixer.supports(d)]
        if not matching:
            continue
        edits = []
        for diagnostic in matching:
            current = SourceFile(source.path, content)
            edits.extend(fixer.plan(FixContext(current, diagnostic, function_spans=cached_spans)))
        edits = _protected_edits(content, edits)
        unique = {(e.start, e.end, e.replacement, e.rule): e for e in edits}
        if unique:
            content = apply_edits(content, list(unique.values()))
            cached_spans = tuple(function_spans(content))
    return SourceFile(source.path, content)


@app.command()
def check(path: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Scan C sources and print a grouped Norminette report."""
    try:
        files, diagnostics = _scan(path)
    except NorminetteError as error:
        console.print(f"[red]error:[/red] {error}")
        raise typer.Exit(code=2)

    total = print_check_report(console, files, diagnostics)
    if total:
        raise typer.Exit(code=1)


@app.command()
def fix(
    path: Path = typer.Argument(..., exists=True, readable=True),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
) -> None:
    """Apply supported mechanical fixes; structural rules and headers remain untouched."""
    provider = NorminetteProvider()
    registry = create_registry()
    files = discover_files(path)
    changed = 0
    unsupported = 0

    # Read all files once and analyze in a single subprocess call
    sources: dict[Path, SourceFile] = {}
    for file in files:
        sources[file] = SourceFile(file, file.read_text(encoding="utf-8"))

    diagnostics_by_file = provider.analyze_batch(files)

    changed_files: list[Path] = []
    for file in files:
        original = sources[file]
        diagnostics = diagnostics_by_file.get(file, [])
        unsupported += sum(1 for d in diagnostics if not registry.find(d.rule))
        fixed = _apply_file(original, diagnostics, registry)
        if fixed.content == original.content:
            continue
        changed += 1
        changed_files.append(file)
        console.print(f"[yellow]•[/yellow] {file} [green]fixes planned[/green]")
        if not dry_run:
            file.write_text(fixed.content, encoding="utf-8")
            sources[file] = fixed

    console.print()
    if dry_run:
        console.print(
            f"[bold]{changed}[/bold] file(s) would change; "
            f"[yellow]{unsupported}[/yellow] unsupported violation(s) remain."
        )
        console.print("[dim]Dry run: no files were changed.[/dim]")
        return

    # Re-analyze only changed files
    remaining = 0
    if changed_files:
        reanalysis = provider.analyze_batch(changed_files)
        for diags in reanalysis.values():
            remaining += len(diags)

    if remaining:
        console.print(
            f"[yellow]✓[/yellow] Applied fixes to [bold]{changed}[/bold] file(s). "
            f"[yellow]{remaining}[/yellow] violation(s) still require attention."
        )
    else:
        console.print(
            f"[green]✓[/green] Applied fixes to [bold]{changed}[/bold] file(s). "
            "Norminette is clean."
        )


if __name__ == "__main__":
    app()
