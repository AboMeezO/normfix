from __future__ import annotations

from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer
from normfix.rules.formatting.helpers import is_preprocessor, line_ranges
from normfix.rules.formatting.layout import function_spans, parse_declaration


class EmptyLineFixer(Fixer):
    id = "empty-lines"
    description = "Enforce one blank line after declarations and none elsewhere."
    rule_codes = {
        "EMPTY_LINE_FUNCTION",
        "SPACE_EMPTY_LINE",
        "NL_AFTER_VAR_DECL",
    }
    priority = 300

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        lines = list(line_ranges(context.source.content))
        edits: list[Edit] = []
        newline = "\r\n" if "\r\n" in context.source.content else "\n"

        for span in function_spans(context.source.content):
            body_start = span.body_start_line
            body_end = span.end_line - 1
            declaration_end = self._declaration_end(lines, body_start, body_end)

            for index in range(body_start, body_end):
                _, start, line = lines[index]
                if line.strip():
                    continue
                keep = declaration_end is not None and index == declaration_end + 1
                if keep:
                    if line != "":
                        edits.append(Edit(start, start + len(line), "", self.id))
                else:
                    edits.append(Edit(start, self._line_end(lines, index), "", self.id))

            if declaration_end is not None:
                next_index = declaration_end + 1
                if next_index < body_end and lines[next_index][2].strip():
                    end = lines[declaration_end][1] + len(lines[declaration_end][2])
                    edits.append(Edit(end, end, newline, self.id))

        return edits

    @staticmethod
    def _declaration_end(lines, start: int, end: int) -> int | None:
        last = None
        index = start
        while index < end:
            _, line_start, line = lines[index]
            declaration = parse_declaration(line, index, line_start)
            if declaration and "=" not in declaration.declarator:
                last = index
                index += 1
                continue
            if not line.strip() and last is not None:
                index += 1
                continue
            break
        return last

    @staticmethod
    def _line_end(lines, index: int) -> int:
        if index + 1 < len(lines):
            return lines[index + 1][1]
        return lines[index][1] + len(lines[index][2])


class PreprocessorSpacingFixer(Fixer):
    id = "nl-after-preproc"
    description = "Separate a preprocessor block from following code."
    rule_codes = {"NL_AFTER_PREPROC"}
    priority = 310

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        lines = list(line_ranges(context.source.content))
        edits = []
        newline = "\r\n" if "\r\n" in context.source.content else "\n"
        index = 0
        while index < len(lines):
            if not is_preprocessor(lines[index][2]):
                index += 1
                continue
            last = index
            while last + 1 < len(lines) and is_preprocessor(lines[last + 1][2]):
                last += 1
            next_index = last + 1
            if next_index < len(lines) and lines[next_index][2].strip():
                end = lines[last][1] + len(lines[last][2])
                edits.append(Edit(end, end, newline, self.id))
            index = next_index
        return edits
