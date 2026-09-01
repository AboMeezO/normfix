import pytest

from normfix.core.models import Edit
from normfix.fixing.engine import EditConflictError, apply_edits


def test_apply_edits_from_right_to_left() -> None:
    result = apply_edits(
        "abcdef",
        [
            Edit(1, 2, "X", "one"),
            Edit(4, 6, "YZ", "two"),
        ],
    )

    assert result.source == "aXcdYZ"


def test_overlapping_edits_are_rejected() -> None:
    with pytest.raises(EditConflictError):
        apply_edits(
            "abcdef",
            [
                Edit(1, 4, "X", "one"),
                Edit(3, 5, "Y", "two"),
            ],
        )


def test_edits_are_idempotent_for_empty_change() -> None:
    result = apply_edits("abc", [])
    assert result.source == "abc"
    assert result.edits == ()
