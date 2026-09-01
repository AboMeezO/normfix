from __future__ import annotations

import re

from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer
from normfix.rules.formatting.helpers import is_preprocessor, line_ranges

_CTRL_FLOW = re.compile(
    r"^\s*(if|else|for|while|do)\b"
)


class IndentationFixer(Fixer):
    id = "indentation"
    description = "Normalize C block indentation to tabs."
    rule_codes = {"TOO_FEW_TAB", "TOO_MANY_TAB", "SPACE_REPLACE_TAB"}
    priority = 100

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        source = context.source.content
        lines = list(line_ranges(source))
        edits: list[Edit] = []
        depth = 0
        in_block_comment = False
        braceless_body = False
        braceless_ctrl = False
        paren_depth = 0
        after_braceless = False

        for index, (_, start, line) in enumerate(lines):
            stripped = line.lstrip(" \t")
            if not stripped:
                continue
            if is_preprocessor(line):
                continue

            if after_braceless:
                depth -= 1
                after_braceless = False

            if braceless_body:
                if stripped.startswith("{"):
                    braceless_body = False
                else:
                    depth += 1
                    braceless_body = False
                    after_braceless = True

            masked, in_block_comment = self._mask_line(
                stripped, in_block_comment
            )
            if not masked.strip():
                continue

            paren_delta = masked.count("(") - masked.count(")")

            closing = masked.lstrip().startswith("}")
            wanted_depth = max(0, depth - int(closing))

            if paren_depth > 0:
                wanted_depth += 1
                paren_depth += paren_delta
                if paren_depth <= 0:
                    paren_depth = 0
                    if braceless_ctrl:
                        braceless_body = True
                        braceless_ctrl = False
            elif _CTRL_FLOW.match(stripped) and paren_delta > 0:
                paren_depth = paren_delta
                braceless_ctrl = True

            replacement = "\t" * wanted_depth + stripped
            if replacement != line:
                edits.append(Edit(
                    start,
                    start + len(line),
                    replacement,
                    self.id,
                ))

            delta = self._brace_delta(masked)
            depth += delta
            depth = max(depth, 0)

            if delta == 0 and _CTRL_FLOW.match(stripped) and "{" not in masked:
                if paren_delta == 0:
                    braceless_body = True

        return edits

    @staticmethod
    def _mask_line(line: str, in_block_comment: bool) -> tuple[str, bool]:
        out: list[str] = []
        quote = None
        escaped = False
        index = 0
        while index < len(line):
            char = line[index]
            nxt = line[index + 1] if index + 1 < len(line) else ""
            if in_block_comment:
                out.append(" ")
                if char == "*" and nxt == "/":
                    out.append(" ")
                    index += 2
                    in_block_comment = False
                    continue
            elif quote:
                out.append(" ")
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
                out.append(" ")
            elif char == "/" and nxt == "*":
                out.extend((" ", " "))
                index += 2
                in_block_comment = True
                continue
            elif char == "/" and nxt == "/":
                break
            else:
                out.append(char)
            index += 1
        return "".join(out), in_block_comment

    @staticmethod
    def _brace_delta(line: str) -> int:
        return line.count("{") - line.count("}")
