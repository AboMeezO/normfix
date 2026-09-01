from normfix.rules.formatting.braces import BracePlacementFixer
from normfix.rules.formatting.declarations import (
    DeclarationAssignmentFixer,
    VariableDeclarationNewlineFixer,
    VariableDeclarationSpacingFixer,
)
from normfix.rules.formatting.empty_lines import EmptyLineFixer, PreprocessorSpacingFixer
from normfix.rules.formatting.indentation import IndentationFixer
from normfix.rules.formatting.spacing import (
    ConsecutiveSpacesFixer,
    FunctionSpacingFixer,
    SpaceReplaceTabFixer,
)
from normfix.rules.formatting.trailing_whitespace import TrailingWhitespaceFixer
from normfix.rules.registry import FixerRegistry


def create_registry() -> FixerRegistry:
    registry = FixerRegistry()
    registry.register(IndentationFixer())
    registry.register(BracePlacementFixer())
    registry.register(ConsecutiveSpacesFixer())
    registry.register(FunctionSpacingFixer())
    registry.register(SpaceReplaceTabFixer())
    registry.register(EmptyLineFixer())
    registry.register(PreprocessorSpacingFixer())
    registry.register(DeclarationAssignmentFixer())
    registry.register(VariableDeclarationSpacingFixer())
    registry.register(VariableDeclarationNewlineFixer())
    registry.register(TrailingWhitespaceFixer())
    return registry
