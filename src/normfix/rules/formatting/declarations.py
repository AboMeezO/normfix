from __future__ import annotations

from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer
from normfix.rules.formatting.helpers import line_ranges
from normfix.rules.formatting.layout import (
    declaration_target_column,
    function_spans,
    parse_declaration,
    tabs_to_column,
    visual_width,
)


class DeclarationAssignmentFixer(Fixer):
    id = "declaration-assignment"
    description = "Split local declarations from their initial assignments."
    rule_codes = {"DECL_ASSIGN_LINE"}
    priority = 400

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits: list[Edit] = []
        for _, start, line in line_ranges(context.source.content):
            declaration = parse_declaration(line, 0, start)
            if not declaration or "=" not in declaration.declarator:
                continue
            name, value = self._split_assignment(declaration.declarator)
            if value is None:
                continue
            indent = declaration.indent
            replacement = (
                f"{indent}{declaration.type_text} {name};\n"
                f"{indent}{self._assignment_name(name)} = {value};"
            )
            edits.append(Edit(start, start + len(line), replacement, self.id))
        return edits

    @staticmethod
    def _assignment_name(declarator: str) -> str:
        return declarator.strip().lstrip("*").strip().split("[", 1)[0].strip()

    @staticmethod
    def _split_assignment(item: str) -> tuple[str, str | None]:
        quote = None
        escaped = False
        depth = 0
        for index, char in enumerate(item):
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in "'\"":
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "=" and depth == 0:
                previous = item[index - 1] if index else ""
                following = item[index + 1] if index + 1 < len(item) else ""
                if previous in "=!<>+-*/%&|" or following == "=":
                    continue
                return item[:index].strip(), item[index + 1:].strip()
        return item.strip(), None


class VariableDeclarationSpacingFixer(Fixer):
    id = "variable-declaration-spacing"
    description = "Align local variable names on the next tab stop."
    rule_codes = {"MISALIGNED_VAR_DECL", "SPACE_REPLACE_TAB", "DECL_ASSIGN_LINE"}
    priority = 410

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits: list[Edit] = []
        lines = list(line_ranges(context.source.content))
        for span in function_spans(context.source.content):
            declarations = self._leading_declarations(lines, span)
            if not declarations:
                continue
            types = [item.type_text for item in declarations]
            target = declaration_target_column(types, declarations[0].indent)
            for item in declarations:
                start_column = visual_width(item.indent + item.type_text)
                tabs = tabs_to_column(start_column, target)
                replacement = (
                    item.indent
                    + item.type_text
                    + "\t" * tabs
                    + item.declarator
                    + ";"
                )
                original = lines[item.line_index][2]
                if replacement != original:
                    edits.append(Edit(
                        item.start,
                        item.start + len(original),
                        replacement,
                        self.id,
                    ))
        return edits

    @staticmethod
    def _leading_declarations(lines, span):
        declarations = []
        index = span.body_start_line
        end_index = span.end_line - 1
        while index < end_index:
            line_number, start, line = lines[index]
            declaration = parse_declaration(line, index, start)
            if declaration and "=" not in declaration.declarator:
                declarations.append(declaration)
                index += 1
                continue
            if not line.strip() and declarations:
                index += 1
                continue
            break
        return declarations


class VariableDeclarationNewlineFixer(Fixer):
    id = "nl-after-var-decl"
    description = "Keep exactly one blank line after local declarations."
    rule_codes = {"NL_AFTER_VAR_DECL", "EMPTY_LINE_FUNCTION", "SPACE_EMPTY_LINE", "DECL_ASSIGN_LINE"}
    priority = 420

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits: list[Edit] = []
        lines = list(line_ranges(context.source.content))
        newline = "\r\n" if "\r\n" in context.source.content else "\n"
        for span in function_spans(context.source.content):
            declarations = []
            index = span.body_start_line
            end_index = span.end_line - 1
            while index < end_index:
                line_number, start, line = lines[index]
                declaration = parse_declaration(line, index, start)
                if declaration and "=" not in declaration.declarator:
                    declarations.append(index)
                    index += 1
                    continue
                if not line.strip() and declarations:
                    index += 1
                    continue
                break
            if not declarations:
                continue
            last = declarations[-1]
            next_index = last + 1
            if next_index < end_index and lines[next_index][2].strip():
                end = lines[last][1] + len(lines[last][2])
                edits.append(Edit(end, end, newline, self.id))
        return edits
