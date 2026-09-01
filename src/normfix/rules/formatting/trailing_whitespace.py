from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer


class TrailingWhitespaceFixer(Fixer):
    id = "trailing-whitespace"
    description = "Remove trailing whitespace from source lines."
    rule_codes = {"TRAILING_SPACE", "SPACE_EMPTY_LINE"}
    priority = 900

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        edits: list[Edit] = []
        offset = 0
        for line in context.source.content.splitlines(keepends=True):
            content = line.rstrip("\r\n")
            stripped = content.rstrip(" \t")
            if stripped != content:
                edits.append(
                    Edit(
                        start=offset + len(stripped),
                        end=offset + len(content),
                        replacement="",
                        rule=self.id,
                    )
                )
            offset += len(line)
        return edits
