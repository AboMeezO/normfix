from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.text import Text

from normfix.presentation.styles import (
    COUNT,
    DIM,
    ERROR,
    FILE,
    RULE,
    SUCCESS,
    SUMMARY,
    TITLE,
)


def print_check_report(
    console: Console,
    files: list[Path],
    diagnostics_by_file: dict[Path, list],
) -> int:
    total = sum(len(items) for items in diagnostics_by_file.values())
    rule_counts = Counter(
        diagnostic.rule
        for diagnostics in diagnostics_by_file.values()
        for diagnostic in diagnostics
    )

    title = Text("NormFix")
    title.stylize(TITLE)
    console.print(title)
    console.print(Text("───────", style=DIM))
    console.print()

    for file in files:
        diagnostics = diagnostics_by_file.get(file, [])
        if not diagnostics:
            continue

        console.print(Text(str(file), style=FILE))
        for rule, count in sorted(Counter(d.rule for d in diagnostics).items()):
            line = Text("  ✗ ", style=ERROR)
            line.append(f"{rule:<24}", style=RULE)
            line.append(str(count), style=COUNT)
            console.print(line)
        console.print()

    console.print(Text("─" * 32, style=DIM))
    summary = Text()
    summary.append(f"{len(files)} files", style=SUMMARY)
    summary.append("  •  ", style=DIM)
    summary.append(f"{total} violations", style=COUNT if total else SUCCESS)
    summary.append("  •  ", style=DIM)
    summary.append(f"{len(rule_counts)} rules", style=SUMMARY)
    console.print(summary)

    if not total:
        console.print(Text("✓ All discovered files are Norminette-clean.", style=SUCCESS))

    return total
