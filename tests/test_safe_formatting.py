from dataclasses import dataclass
from pathlib import Path

from normfix.cli.app import _apply_file
from normfix.core.models import SourceFile
from normfix.rules.builtin import create_registry


@dataclass(frozen=True)
class Diagnostic:
    rule: str


def apply(source_text: str, *rules: str) -> str:
    diagnostics = [Diagnostic(rule) for rule in rules]
    return _apply_file(
        SourceFile(Path("test.c"), source_text),
        diagnostics,
        create_registry(),
    ).content


def test_invalid_header_is_never_touched() -> None:
    source = "/* user header - leave this alone */\nint foo(void)\n{\n    return (0);\n}"
    fixed = apply(source, "INVALID_HEADER", "TOO_FEW_TAB", "BRACE_SHOULD_EOL")

    assert fixed.startswith("/* user header - leave this alone */\n")
    assert "# **************************************************************************** #" not in fixed


def test_function_body_indentation_is_preserved_correctly() -> None:
    source = (
        "int ft_isalpha(char c)\n"
        "{\n"
        "    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))\n"
        "        return (1);\n"
        "    return (0);\n"
        "}"
    )
    fixed = apply(source, "TOO_FEW_TAB", "SPACE_BEFORE_FUNC", "BRACE_SHOULD_EOL")

    assert "int\tft_isalpha(char c)\n" in fixed
    assert "\tif ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))\n" in fixed
    assert "\t\treturn (1);\n" in fixed
    assert "\treturn (0);\n" in fixed
    assert fixed.endswith("}\n")


def test_local_declarations_use_common_tab_stop() -> None:
    source = (
        "void test(void)\n"
        "{\n"
        "    char c;\n"
        "    int index;\n"
        "    unsigned char *data;\n"
        "    index = 0;\n"
        "}"
    )
    fixed = apply(
        source,
        "MISALIGNED_VAR_DECL",
        "SPACE_REPLACE_TAB",
        "NL_AFTER_VAR_DECL",
    )

    assert "\tchar\t\tc;\n" in fixed
    assert "\tint\t\tindex;\n" in fixed
    assert "\tunsigned char\t*data;\n" in fixed
    assert "\n\tindex = 0;\n" in fixed


def test_declaration_assignment_is_split_before_alignment() -> None:
    source = (
        "void test(void)\n"
        "{\n"
        "    unsigned char *data = (unsigned char *)0;\n"
        "    data = 0;\n"
        "}"
    )
    fixed = apply(source, "DECL_ASSIGN_LINE", "MISALIGNED_VAR_DECL")

    assert "unsigned char\t*data;" in fixed
    assert "\n\tdata = (unsigned char *)0;" in fixed
