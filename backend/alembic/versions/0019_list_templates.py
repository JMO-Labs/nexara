# ruff: noqa: E501
"""lists: template, list, member, item, signup, completion tables + seeds

Revision ID: 0019_list_templates
Revises: a78f91338679
"""

import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID

from alembic import op

revision = "0019_list_templates"
down_revision = "a78f91338679"
branch_labels = None
depends_on = None

# Creation order (drop is the reverse).
TABLES = [
    "list_template",
    "list_template_field",
    "list_template_item",
    "list",
    "list_member",
    "list_item",
    "list_item_signup",
    "list_item_completion",
]

_KINDS = ["item", "signup", "completed", "expiring", "member"]
NOTIF_COLUMNS = [f"notif_list_{k}_{ch}" for k in _KINDS for ch in ("inapp", "email")]


def _f(key: str, label: str, type_key: str, required: bool = False, **config: object) -> dict:
    return {
        "key": key,
        "label": label,
        "type_key": type_key,
        "required": required,
        "config": config,
    }


SEED_TEMPLATES = [
    {
        "name": "Gift List",
        "description": "Wish list where members can claim gifts.",
        "category": "gift",
        "icon": "🎁",
        "color": "#C2410C",
        "fields": [
            _f("title", "Title", "text", True),
            _f("link", "Link", "url"),
            _f("price", "Price", "number"),
            _f("note", "Note", "text"),
            _f("claimed", "Claimed", "signup", quantity=1),
        ],
    },
    {
        "name": "Potluck",
        "description": "Sign up to bring a dish.",
        "category": "potluck",
        "icon": "🍲",
        "color": "#15803D",
        "fields": [
            _f("dish", "Dish", "text", True),
            _f("category", "Category", "select", options=["Main", "Side", "Dessert", "Drink"]),
            _f(
                "dietary",
                "Dietary",
                "multiselect",
                options=["Vegetarian", "Vegan", "Gluten-free", "Nut-free"],
            ),
            _f("quantity", "Quantity", "number"),
            _f("serves", "Serves", "number"),
        ],
    },
    {
        "name": "To-do",
        "description": "Simple shared task list.",
        "category": "todo",
        "icon": "✅",
        "color": "#1D4ED8",
        "fields": [
            _f("task", "Task", "text", True),
            _f("due", "Due date", "date"),
            _f("priority", "Priority", "select", options=["Low", "Medium", "High"]),
            _f("done", "Done", "checkbox"),
        ],
    },
    {
        "name": "Contact",
        "description": "Shared contact directory.",
        "category": "contact",
        "icon": "📇",
        "color": "#7E22CE",
        "fields": [
            _f("name", "Name", "text", True),
            _f("phone", "Phone", "user_pull", source="phone"),
            _f("email", "Email", "email"),
            _f("address", "Address", "text"),
            _f("birthday", "Birthday", "date"),
            _f("notes", "Notes", "text"),
        ],
    },
]


def _id() -> sa.Column:
    return sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def _fk(name: str, target: str, ondelete: str | None, nullable: bool = True, **kw) -> sa.Column:
    return sa.Column(
        name, UUID(as_uuid=True), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable, **kw
    )


def _ts() -> list[sa.Column]:
    now = sa.text("now()")
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _fts(table: str, expr: str) -> sa.Column:
    return sa.Column("search_fts", TSVECTOR, sa.Computed(expr, persisted=True))


def _jsonb(name: str, default: str) -> sa.Column:
    return sa.Column(name, JSONB, nullable=False, server_default=sa.text(f"'{default}'::jsonb"))


def _int(name: str, default: str = "0") -> sa.Column:
    return sa.Column(name, sa.Integer, nullable=False, server_default=default)


def _bool(name: str, default: str = "false") -> sa.Column:
    return sa.Column(name, sa.Boolean, nullable=False, server_default=default)


def _created_tables() -> None:
    cid = lambda: _fk("community_id", "communities.id", "CASCADE", False)  # noqa: E731
    op.create_table(
        "list_template",
        _id(),
        cid(),
        _fk("author_id", "users.id", "SET NULL"),
        _bool("is_system"),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.Text),
        sa.Column("icon", sa.Text),
        sa.Column("color", sa.Text),
        _fk("cover_media_id", "media.id", "SET NULL"),
        _bool("is_shared"),
        *_ts(),
        _fts(
            "list_template",
            "to_tsvector('english', coalesce(name,'') || ' ' || coalesce(description,''))",
        ),
    )
    op.create_table(
        "list_template_field",
        _id(),
        _fk("template_id", "list_template.id", "CASCADE", False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("type_key", sa.Text, nullable=False),
        _bool("required"),
        _jsonb("config", "{}"),
        sa.UniqueConstraint("template_id", "key", name="uq_list_template_field_key"),
    )
    op.create_table(
        "list_template_item",
        _id(),
        _fk("template_id", "list_template.id", "CASCADE", False),
        sa.Column("position", sa.Integer, nullable=False),
        _jsonb("values", "{}"),
    )
    op.create_table(
        "list",
        _id(),
        cid(),
        _fk("template_id", "list_template.id", "SET NULL"),
        _fk("owner_id", "users.id", "CASCADE", False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("visibility", sa.Text, nullable=False),
        _fk("subgroup_id", "subgroups.id", "SET NULL"),
        _fk("cover_media_id", "media.id", "SET NULL"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        _jsonb("field_schema", "[]"),
        _int("item_count"),
        _int("completed_count"),
        _int("signup_count"),
        *_ts(),
        _fts(
            "list", "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))"
        ),
        sa.CheckConstraint(
            "visibility IN ('community','subgroup','private','members')", name="ck_list_visibility"
        ),
    )
    op.create_table(
        "list_member",
        _fk("list_id", "list.id", "CASCADE", False, primary_key=True),
        _fk("user_id", "users.id", "CASCADE", False, primary_key=True),
        sa.Column("role", sa.Text, nullable=False, server_default="viewer"),
        _bool("share_personal"),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "list_item",
        _id(),
        _fk("list_id", "list.id", "CASCADE", False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        _jsonb("values", "{}"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        _bool("completed"),
        sa.Column("lat", sa.Float),
        sa.Column("lon", sa.Float),
        sa.Column("signup_quantity_needed", sa.Integer),
        *_ts(),
    )
    op.create_table(
        "list_item_signup",
        _fk("item_id", "list_item.id", "CASCADE", False, primary_key=True),
        _fk("user_id", "users.id", "CASCADE", False, primary_key=True),
        _int("quantity", "1"),
        sa.Column("note", sa.Text),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "list_item_completion",
        _fk("item_id", "list_item.id", "CASCADE", False, primary_key=True),
        _fk("user_id", "users.id", "CASCADE", False, primary_key=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def _indexes() -> None:
    op.create_index("ix_list_template_community_id", "list_template", ["community_id"])
    op.create_index(
        "ix_list_template_search_fts", "list_template", ["search_fts"], postgresql_using="gin"
    )
    op.create_index("ix_list_template_field_template_id", "list_template_field", ["template_id"])
    op.create_index("ix_list_template_item_template_id", "list_template_item", ["template_id"])
    op.create_index("ix_list_community_id", "list", ["community_id"])
    op.create_index("ix_list_owner_id", "list", ["owner_id"])
    op.create_index("ix_list_search_fts", "list", ["search_fts"], postgresql_using="gin")
    op.create_index("ix_list_member_user_id", "list_member", ["user_id"])
    op.create_index("ix_list_item_list_id", "list_item", ["list_id"])
    op.create_index("ix_list_item_signup_user_id", "list_item_signup", ["user_id"])


def _seed() -> None:
    """@brief Insert the 4 system templates per community, skipping existing ones."""
    conn = op.get_bind()
    communities = [r[0] for r in conn.execute(sa.text("SELECT id FROM communities"))]
    for cid in communities:
        for t in SEED_TEMPLATES:
            row = conn.execute(
                sa.text(
                    "INSERT INTO list_template (community_id, is_system, is_shared, name,"
                    " description, category, icon, color) SELECT :cid, true, true, :name,"
                    " :description, :category, :icon, :color WHERE NOT EXISTS (SELECT 1 FROM"
                    " list_template WHERE community_id = :cid AND is_system AND category = :category"
                    " AND deleted_at IS NULL) RETURNING id"
                ),
                {
                    "cid": cid,
                    **{k: t[k] for k in ("name", "description", "category", "icon", "color")},
                },
            ).first()
            if row is None:
                continue
            for pos, f in enumerate(t["fields"]):
                conn.execute(
                    sa.text(
                        "INSERT INTO list_template_field (template_id, position, key, label,"
                        " type_key, required, config) VALUES (:tid, :pos, :key, :label,"
                        " :type_key, :required, CAST(:config AS jsonb))"
                    ),
                    {
                        "tid": row[0],
                        "pos": pos,
                        **{k: f[k] for k in ("key", "label", "type_key", "required")},
                        "config": json.dumps(f["config"]),
                    },
                )


def upgrade() -> None:
    _created_tables()
    _indexes()
    for col in NOTIF_COLUMNS:
        default = "true" if col.endswith("_inapp") else "false"
        op.add_column(
            "user_settings",
            sa.Column(col, sa.Boolean, nullable=False, server_default=default),
        )
    _seed()


def downgrade() -> None:
    for col in reversed(NOTIF_COLUMNS):
        op.drop_column("user_settings", col)
    for table in reversed(TABLES):
        op.drop_table(table)
