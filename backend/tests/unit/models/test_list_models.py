"""
@file test_list_models.py
@brief Unit tests for list and list-template ORM model structure (matches 0026).
"""

import app.models  # noqa: F401
from app.models import (
    List,
    ListItem,
    ListItemCompletion,
    ListItemSignup,
    ListMember,
    ListTemplate,
    ListTemplateField,
    ListTemplateItem,
)

TS = {"created_at", "updated_at", "deleted_at"}

EXPECTED = {
    ListTemplate: (
        "list_template",
        {
            "id",
            "community_id",
            "author_id",
            "is_system",
            "name",
            "description",
            "category",
            "icon",
            "color",
            "cover_media_id",
            "is_shared",
            "search_fts",
        }
        | TS,
        ["id"],
    ),
    ListTemplateField: (
        "list_template_field",
        {"id", "template_id", "position", "key", "label", "type_key", "required", "config"},
        ["id"],
    ),
    ListTemplateItem: (
        "list_template_item",
        {"id", "template_id", "position", "values"},
        ["id"],
    ),
    List: (
        "list",
        {
            "id",
            "community_id",
            "template_id",
            "owner_id",
            "title",
            "description",
            "visibility",
            "subgroup_id",
            "cover_media_id",
            "expires_at",
            "notified_at",
            "status",
            "field_schema",
            "item_count",
            "completed_count",
            "signup_count",
            "search_fts",
        }
        | TS,
        ["id"],
    ),
    ListMember: (
        "list_member",
        {"list_id", "user_id", "role", "share_personal", "added_at"},
        ["list_id", "user_id"],
    ),
    ListItem: (
        "list_item",
        {
            "id",
            "list_id",
            "position",
            "values",
            "due_at",
            "completed",
            "lat",
            "lon",
            "signup_quantity_needed",
        }
        | TS,
        ["id"],
    ),
    ListItemSignup: (
        "list_item_signup",
        {"item_id", "user_id", "quantity", "note", "claimed_at"},
        ["item_id", "user_id"],
    ),
    ListItemCompletion: (
        "list_item_completion",
        {"item_id", "user_id", "completed_at"},
        ["item_id", "user_id"],
    ),
}


def test_tables_columns_and_pks():
    for model, (name, cols, pk) in EXPECTED.items():
        assert model.__tablename__ == name
        assert {c.name for c in model.__table__.columns} == cols, name
        assert [c.name for c in model.__table__.primary_key.columns] == pk, name


def test_template_field_unique_constraint():
    names = {c.name for c in ListTemplateField.__table__.constraints}
    assert "uq_list_template_field_key" in names


def test_relationships_back_populate():
    assert ListTemplate.fields.property.back_populates == "template"
    assert ListTemplate.items.property.back_populates == "template"
    assert "delete-orphan" in ListTemplate.fields.property.cascade
    assert ListTemplateField.template.property.back_populates == "fields"
    assert ListTemplateItem.template.property.back_populates == "items"
    assert List.items.property.back_populates == "list_obj"
    assert List.members.property.back_populates == "list_obj"
    assert ListMember.list_obj.property.back_populates == "members"
    assert ListItem.list_obj.property.back_populates == "items"
    assert ListItem.signups.property.back_populates == "item"
    assert ListItem.completions.property.back_populates == "item"
