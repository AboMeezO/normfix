from pathlib import Path

from normfix.core.models import Diagnostic, SourceFile, SourceLocation
from normfix.rules.base import FixContext
from normfix.rules.formatting.declarations import VariableDeclarationSpacingFixer
from normfix.rules.formatting.empty_lines import EmptyLineFixer


def _context(text: str, rule: str) -> FixContext:
    source = SourceFile(Path("test.c"), text)
    diagnostic = Diagnostic(
        rule=rule,
        location=SourceLocation(1, 1),
        message="",
        file=source.path,
    )
    return FixContext(source, diagnostic)


def _apply(text: str, edits) -> str:
    for edit in sorted(edits, key=lambda item: item.start, reverse=True):
        text = text[:edit.start] + edit.replacement + text[edit.end:]
    return text


def test_declaration_alignment_uses_tab_stops() -> None:
    text = """int\tmain(void)\n{\n\tchar c;\n\tint i;\n\n\treturn (0);\n}\n"""
    fixer = VariableDeclarationSpacingFixer()
    result = fixer.plan(_context(text, "MISALIGNED_VAR_DECL"))
    fixed = _apply(text, result)

    assert "\tchar\tc;" in fixed
    assert "\tint\t\ti;" in fixed


def test_declaration_block_has_one_blank_line_after_it() -> None:
    text = """int\tmain(void)\n{\n\tchar\tc;\n\tint\t\ti;\n\n\n\treturn (0);\n\n}\n"""
    fixer = EmptyLineFixer()
    result = fixer.plan(_context(text, "EMPTY_LINE_FUNCTION"))
    fixed = _apply(text, result)

    assert "\tint\t\ti;\n\n\treturn" in fixed
    assert "\n\n\n" not in fixed
    assert "return (0);\n\n}" not in fixed
