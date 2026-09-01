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


def tabs_to_column(start_column: int, target_column: int) -> int:
    count = 0
    column = start_column
    while column < target_column:
        column += 8 - (column % 8)
        count += 1
    return count


def declaration_target_column(types: list[str], indent: str) -> int:
    max_width = max(visual_width(indent + type_text) for type_text in types)
    return ((max_width // 8) + 1) * 8
