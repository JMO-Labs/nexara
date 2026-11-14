"""
@file test_list_schemas.py
@brief Validation tests for list and list-template schemas.
"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.list import (
    ListCreate,
    ListItemCreate,
    ListItemOut,
    ListMemberOut,
    ListUpdate,
    SignupClaim,
)
from app.schemas.list_template import (
    ListTemplateCreate,
    ListTemplateFieldIn,
    ListTemplateFieldOut,
)


def _field(**kw: object) -> dict[str, object]:
    return {"key": "name", "label": "Name", "type_key": "text", "position": 0, **kw}


def test_field_valid_defaults() -> None:
    f = ListTemplateFieldIn(**_field())
    assert f.required is False and f.config == {}


@pytest.mark.parametrize("key", ["Bad", "has space", "a-b", ""])
def test_field_key_pattern_rejected(key: str) -> None:
    with pytest.raises(ValidationError):
        ListTemplateFieldIn(**_field(key=key))


def test_field_position_and_label_bounds() -> None:
    with pytest.raises(ValidationError):
        ListTemplateFieldIn(**_field(position=-1))
    with pytest.raises(ValidationError):
        ListTemplateFieldIn(**_field(label=""))


def test_field_out_from_attributes() -> None:
    obj = SimpleNamespace(id=uuid.uuid4(), **_field(required=True, config={}))
    assert ListTemplateFieldOut.model_validate(obj).required is True


def test_template_create_defaults() -> None:
    t = ListTemplateCreate(name="Potluck")
    assert t.category is None and t.fields == [] and t.items == []


def test_list_create_defaults_and_visibility() -> None:
    c = ListCreate(title="T")
    assert c.visibility == "community" and c.field_schema == []
    with pytest.raises(ValidationError):
        ListCreate(title="T", visibility="public")


def test_list_update_all_optional() -> None:
    assert ListUpdate().model_dump(exclude_unset=True) == {}


def test_item_create_position_ge_zero() -> None:
    assert ListItemCreate(position=0, values={"a": 1}).position == 0
    with pytest.raises(ValidationError):
        ListItemCreate(position=-1)


def test_signup_quantity_ge_one() -> None:
    assert SignupClaim().quantity == 1
    with pytest.raises(ValidationError):
        SignupClaim(quantity=0)


def test_item_and_member_out_from_attributes() -> None:
    now = datetime.now(UTC)
    item = SimpleNamespace(
        id=uuid.uuid4(),
        position=1,
        values={},
        due_at=None,
        completed=False,
        lat=None,
        lon=None,
        signup_quantity_needed=3,
    )
    assert ListItemOut.model_validate(item).signup_quantity_needed == 3
    m = SimpleNamespace(
        list_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role="viewer",
        share_personal=False,
        added_at=now,
    )
    assert ListMemberOut.model_validate(m).role == "viewer"
