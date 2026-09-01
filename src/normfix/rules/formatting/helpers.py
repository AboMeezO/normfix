import re

from normfix.core.models import Edit


def line_ranges(source: str):
    offset = 0
    for line_number, line in enumerate(source.splitlines(keepends=True), 1):
        body = line.rstrip("\r\n")
        yield line_number, offset, body
        offset += len(line)


def edit_line(start: int, line: str, replacement: str, rule: str) -> Edit:
    return Edit(start=start, end=start + len(line), replacement=replacement, rule=rule)


def is_preprocessor(line: str) -> bool:
    return line.lstrip().startswith("#")


def leading_depth(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def declaration_match(line: str):
    text = line.strip()
    return re.match(
        r"^(?P<prefix>(?:(?:const|volatile|static|unsigned|signed|long|short)\s+)*(?:void|char|short|int|long|float|double|size_t|ssize_t|struct\s+\w+|enum\s+\w+|union\s+\w+)(?:\s*\*)*)\s+(?P<decl>[^;]+);\s*$",
        text,
    )


def is_simple_declaration(line: str) -> bool:
    return declaration_match(line) is not None


def split_declarators(text: str) -> list[str] | None:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote = None
    escaped = False
    for char in text:
        if quote:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            current.append(char)
        elif char in "([{":
            depth += 1
            current.append(char)
        elif char in ")]}":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts if len(parts) > 1 else None
