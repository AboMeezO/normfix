from normfix.rules.base import Fixer


class FixerRegistry:
    def __init__(self) -> None:
        self._fixers: list[Fixer] = []

    def register(self, fixer: Fixer) -> None:
        if any(item.id == fixer.id for item in self._fixers):
            raise ValueError(f"Fixer already registered: {fixer.id}")
        self._fixers.append(fixer)
        self._fixers.sort(key=lambda item: (item.priority, item.id))

    def all(self) -> tuple[Fixer, ...]:
        return tuple(self._fixers)

    def find(self, rule: str) -> tuple[Fixer, ...]:
        return tuple(
            fixer for fixer in self._fixers
            if fixer.id == rule or rule in getattr(fixer, "rule_codes", ())
        )
