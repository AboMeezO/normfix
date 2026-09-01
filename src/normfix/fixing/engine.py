from dataclasses import dataclass

from normfix.core.models import Edit


class EditConflictError(ValueError):
    pass


@dataclass(frozen=True)
class AppliedEdits:
    source: str
    edits: tuple[Edit, ...]


def validate_edits(edits: list[Edit]) -> tuple[Edit, ...]:
    ordered = tuple(sorted(edits, key=lambda edit: (edit.start, edit.end)))
    previous_end = -1
    for edit in ordered:
        if edit.start < 0 or edit.end < edit.start:
            raise ValueError(f"Invalid edit range: {edit}")
        if edit.start < previous_end:
            raise EditConflictError(
                f"Overlapping edits: {edit}"
            )
        previous_end = edit.end
    return ordered


def apply_edits(source: str, edits: list[Edit]) -> AppliedEdits:
    ordered = validate_edits(edits)
    result = source
    for edit in reversed(ordered):
        result = result[:edit.start] + edit.replacement + result[edit.end:]
    return AppliedEdits(result, ordered)
