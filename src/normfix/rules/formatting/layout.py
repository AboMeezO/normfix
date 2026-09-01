from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class FunctionSpan:
    start_line: int
    start_offset: int
    body_start_line: int
    body_start_offset: int
    end_line: int
    end_offset: int


@dataclass(frozen=True)
class VariableDeclaration:
    line_index: int
    start: int
    indent: str
    type_text: str
    declarator: str
    name: str


_QUALIFIERS = r"(?:(?:const|volatile|static|extern|unsigned|signed|long|short)\s+)*"
_TYPE = (
    rf"(?:{_QUALIFIERS}"
    r"(?:struct\s+[A-Za-z_]\w*|enum\s+[A-Za-z_]\w*|"
    r"union\s+[A-Za-z_]\w*|void|char|short|int|long|float|double|"
    r"size_t|ssize_t|bool|[A-Za-z_]\w*))"
)
_DECLARATOR = (
    r"(?P<decl>\*+\s*)?"
    r"(?P<name>[A-Za-z_]\w*)"
    r"(?:\s*\[[^]]*\])?"
    r"(?:\s*=.*)?"
)
_DECLARATION = re.compile(
    rf"^(?P<type>{_TYPE})\s+{_DECLARATOR}\s*;\s*$"
)


def _lexical_chars(source: str):
    state = "code"
    escaped = False
    index = 0
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == '"':
                state = "string"
                yield " "
            elif char == "'":
                state = "char"
                yield " "
            elif char == "/" and nxt == "/":
                state = "line_comment"
                yield " "
                index += 1
                yield " "
            elif char == "/" and nxt == "*":
                state = "block_comment"
                yield " "
                index += 1
                yield " "
            else:
                yield char
        elif state == "string":
            yield " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                state = "code"
        elif state == "char":
            yield " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                state = "code"
        elif state == "line_comment":
            yield "\n" if char == "\n" else " "
            if char == "\n":
                state = "code"
        else:
            yield "\n" if char == "\n" else " "
            if char == "*" and nxt == "/":
                index += 1
                yield " "
                state = "code"
        index += 1


def function_spans(source: str) -> list[FunctionSpan]:
    masked = "".join(_lexical_chars(source))
    spans: list[FunctionSpan] = []
    depth = 0
    body_start = None
    for index, char in enumerate(masked):
        if char == "{" and depth == 0:
            line = masked.count("\n", 0, index) + 1
            prefix = masked[max(0, masked.rfind("\n", 0, index) + 1):index]
            if ")" in prefix:
                body_start = (line, index)
            else:
                prev_newline = masked.rfind("\n", 0, index)
                if prev_newline >= 0:
                    prev_line = masked[max(0, masked.rfind("\n", 0, prev_newline) + 1):prev_newline]
                    if ")" in prev_line:
                        body_start = (line, index)
            depth = 1
        elif char == "{" and depth:
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and body_start:
                brace_line, brace_offset = body_start
                end_line = masked.count("\n", 0, index) + 1
                spans.append(FunctionSpan(
                    start_line=brace_line,
                    start_offset=masked.rfind("\n", 0, brace_offset) + 1,
                    body_start_line=brace_line + 1,
                    body_start_offset=brace_offset + 1,
                    end_line=end_line,
                    end_offset=index,
                ))
                body_start = None
    return spans


def parse_declaration(
    line: str,
    line_index: int,
    start: int,
) -> VariableDeclaration | None:
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    text = line.strip()
    match = _DECLARATION.match(text)
    if not match:
        return None
    type_text = match.group("type").strip()
    declarator = text[match.end("type"):].strip()
    if declarator.endswith(";"):
        declarator = declarator[:-1].rstrip()
    name = match.group("name")
    indent = line[:len(line) - len(line.lstrip(" \t"))]
    return VariableDeclaration(
        line_index=line_index,
        start=start,
        indent=indent,
        type_text=type_text,
        declarator=declarator,
        name=name,
    )


def visual_width(text: str, start_column: int = 0) -> int:
    column = start_column
    for char in text:
        if char == "\t":
            column += 8 - (column % 8)
        else:
            column += 1
    return column


def _norminette_type_score(type_text: str) -> int:
    """Replicate norminette's alignment scoring from check_variable_indent.py.

    norminette counts ``floor((keyword_length + buffer) / 4)`` for each
    type keyword, with a 1-space buffer between keywords.
    """
    score = 0
    buf = 0
    words = type_text.split()
    for i, word in enumerate(words):
        score += (len(word) + buf) // 4
        buf = 1 if i < len(words) - 1 else 0
    return score


def _norminette_gap_tabs(type_text: str, target_score: int) -> int:
    """Return the number of TABs needed between *type_text* and the
    variable name so that the name lands at *target_score* columns
    (counting 1 for the leading TAB + type_score + gap_tabs).
    """
    leading = 1
    return max(0, target_score - leading - _norminette_type_score(type_text))


def declaration_target_column(types: list[str], indent: str) -> int:
    """Return the norminette alignment score that all names should reach.

    The score is: ``1 (leading tab) + max_type_score + 1`` (the +1 is
    the minimum single gap-tab that norminette requires).
    """
    max_score = max(_norminette_type_score(t) for t in types)
    return 1 + max_score + 1


def tabs_to_column(start_column: int, target_column: int) -> int:
    count = 0
    column = start_column
    while column < target_column:
        column += 8 - (column % 8)
        count += 1
    return count
