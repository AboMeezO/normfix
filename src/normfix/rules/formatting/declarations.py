from __future__ import annotations

from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer
from normfix.rules.formatting.helpers import line_ranges
from normfix.rules.formatting.layout import (
    FunctionSpan,
    _norminette_gap_tabs,
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
        lines = list(line_ranges(context.source.content))
        spans = context.function_spans if context.function_spans else function_spans(context.source.content)
        for span in spans:
            block = self._leading_declarations_with_assignments(lines, span)
            if not block:
                continue
            pure_decls, assignments = block
            if not assignments:
                continue
            all_items = sorted(pure_decls + assignments, key=lambda x: x.start)
            start_offset = all_items[0].start
            end_offset = all_items[-1].start + len(lines[all_items[-1].line_index][2])
            original_text = context.source.content[start_offset:end_offset]
            indent = all_items[0].indent
            decl_lines = []
            for item in pure_decls:
                original = lines[item.line_index][2]
                decl_lines.append(original)
            assign_lines = []
            for item in assignments:
                name_part, value = self._split_assignment(item.declarator)
                if value is None:
                    continue
                name = self._assignment_name(name_part)
                stars = name_part.strip()[:len(name_part.strip()) - len(name_part.strip().lstrip("*"))]
                decl_lines.append(f"{item.indent}{item.type_text} {stars}{name};")
                assign_lines.append(f"{item.indent}{name} = {value};")
            new_text = "\n".join(decl_lines + assign_lines)
            if new_text != original_text:
                edits.append(Edit(start_offset, end_offset, new_text, self.id))
        return edits

    @staticmethod
    def _leading_declarations_with_assignments(
        lines: list[tuple[int, int, str]],
        span: FunctionSpan,
    ) -> tuple[list, list]:
        """Collect leading declarations and assignments in a function body.

        Returns (pure_declarations, assignments) where pure_declarations
        are declarations without initializers and assignments are
        declarations with initializers that need to be split.
        """
        pure_decls = []
        assignments = []
        index = span.body_start_line - 1
        end_index = span.end_line - 1
        while index < end_index:
            line_number, start, line = lines[index]
            declaration = parse_declaration(line, index, start)
            if declaration:
                if "=" in declaration.declarator:
                    assignments.append(declaration)
                else:
                    pure_decls.append(declaration)
                index += 1
                continue
            if not line.strip() and (pure_decls or assignments):
                index += 1
                continue
            break
        return pure_decls, assignments

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
        spans = context.function_spans if context.function_spans else function_spans(context.source.content)
        for span in spans:
            declarations = self._leading_declarations(lines, span)
            if not declarations:
                continue
            types = [item.type_text for item in declarations]
            target = declaration_target_column(types, declarations[0].indent)
            for item in declarations:
                tabs = _norminette_gap_tabs(item.type_text, target)
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
        index = span.body_start_line - 1
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
        spans = context.function_spans if context.function_spans else function_spans(context.source.content)
        for span in spans:
            declarations = []
            index = span.body_start_line - 1
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
