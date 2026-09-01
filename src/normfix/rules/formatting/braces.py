from normfix.core.models import Edit
from normfix.rules.base import FixContext, Fixer


class BracePlacementFixer(Fixer):
    id = "file-ending-newline"
    description = "Ensure the file ends with exactly one newline."
    rule_codes = {"BRACE_SHOULD_EOL"}
    priority = 900

    def supports(self, diagnostic) -> bool:
        return diagnostic.rule in self.rule_codes

    def plan(self, context: FixContext) -> list[Edit]:
        source = context.source.content
        if not source:
            return []
        end = len(source.rstrip("\r\n"))
        if end == len(source) - 1 and source.endswith("\n"):
            return []
        return [Edit(end, len(source), "\n", self.id)]
