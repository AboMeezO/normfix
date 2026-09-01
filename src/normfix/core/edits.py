from normfix.core.models import Edit


def apply_edits(source: str, edits: list[Edit]) -> str:
    if not edits:
        return source
    ordered = sorted(edits, key=lambda edit: (edit.start, edit.end))
    previous_end = -1
    for edit in ordered:
        if edit.start < previous_end:
            raise ValueError("Overlapping source edits")
        if edit.start < 0 or edit.end < edit.start or edit.end > len(source):
            raise ValueError("Invalid source edit range")
        previous_end = edit.end
    for edit in reversed(ordered):
        source = source[:edit.start] + edit.replacement + source[edit.end:]
    return source
