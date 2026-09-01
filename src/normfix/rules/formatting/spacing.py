import re

from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer
from normfix.rules.formatting.helpers import line_ranges


class ConsecutiveSpacesFixer(Fixer):
    id = "consecutive-spaces"
    description = "Collapse consecutive code spaces without touching literals."
    rule_codes = {"CONSECUTIVE_SPC"}
    priority = 200

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits = []
        for _, start, line in line_ranges(context.source.content):
            replacement = self._normalize(line)
            if replacement != line:
                edits.append(Edit(start, start + len(line), replacement, self.id))
        return edits

    @staticmethod
    def _normalize(line: str) -> str:
        out: list[str] = []
        quote = None
        escaped = False
        index = 0
        while index < len(line):
            char = line[index]
            nxt = line[index + 1] if index + 1 < len(line) else ""
            if quote:
                out.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                index += 1
                continue
            if char in "'\"":
                quote = char
                out.append(char)
                index += 1
                continue
            if char == "/" and nxt == "/":
                out.append(line[index:])
                break
            if char == " " and index + 1 < len(line):
                out.append(" ")
                index += 1
                while index < len(line) and line[index] == " ":
                    index += 1
                continue
            out.append(char)
            index += 1
        return "".join(out)


class FunctionSpacingFixer(Fixer):
    id = "space-before-function"
    description = "Use a tab between a function return type and name."
    rule_codes = {"SPACE_BEFORE_FUNC"}
    priority = 210

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits = []
        pattern = re.compile(
            r"^(?P<indent>[ \t]*)(?P<type>"
            r"(?:(?:static|extern|const|volatile|unsigned|signed|long|short)\s+)*"
            r"(?:void|char|short|int|long|float|double|size_t|ssize_t|bool|"
            r"struct\s+[A-Za-z_]\w*|enum\s+[A-Za-z_]\w*|"
            r"union\s+[A-Za-z_]\w*|[A-Za-z_]\w*)"
            r")\s+(?P<pointer>\*\s*)?(?P<name>[A-Za-z_]\w*)\s*\("
        )
        for _, start, line in line_ranges(context.source.content):
            match = pattern.match(line)
            if not match:
                continue
            prefix = match.group("indent")
            pointer = "*" if match.group("pointer") else ""
            tail = line[match.end():]
            replacement = (
                prefix
                + match.group("type")
                + "\t"
                + pointer
                + match.group("name")
                + "("
                + tail
            )
            if replacement != line:
                edits.append(Edit(start, start + len(line), replacement, self.id))
        return edits


class SpaceReplaceTabFixer(Fixer):
    id = "space-replace-tab"
    description = "Replace leading indentation spaces with tabs."
    rule_codes = {"SPACE_REPLACE_TAB"}
    priority = 220

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits = []
        for _, start, line in line_ranges(context.source.content):
            if not line or line.lstrip().startswith("#"):
                continue
            leading = len(line) - len(line.lstrip(" \t"))
            if not leading:
                continue
            prefix = line[:leading]
            if " " not in prefix:
                continue
            spaces = len(prefix.replace("\t", ""))
            tabs = spaces // 4
            remainder = spaces % 4
            normalized = "\t" * tabs + " " * remainder
            replacement = normalized + line[leading:]
            if replacement != line:
                edits.append(Edit(start, start + len(line), replacement, self.id))
        return edits
