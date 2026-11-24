"""Two-factor: encrypted TOTP, pending secret, passkeys, community 2FA policy.

@file 0070_twofactor.py
@brief Encrypts users.totp_secret (Fernet); adds totp_pending_secret,
two_factor_required_since, communities.require_2fa and the passkeys table.

Revision ID: 0070_twofactor
Revises: 0069_apprise_admin
"""

import sqlalchemy as sa
from cryptography.fernet import InvalidToken
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, UUID

from alembic import op
from app.core.config import get_settings
from app.core.encryption import decrypt_secret, derive_fernet_key, encrypt_secret

revision = "0070_twofactor"
down_revision = "0069_apprise_admin"
branch_labels = None
depends_on = None

_COMMUNITY = "00000000-0000-0000-0000-000000000001"


def _rewrite(convert) -> None:  # type: ignore[no-untyped-def]
    """@brief Apply ``convert`` to every non-null users.totp_secret."""
    conn = op.get_bind()
    key = derive_fernet_key(get_settings().SECRET_KEY)
    rows = conn.execute(sa.text("SELECT id, totp_secret FROM users WHERE totp_secret IS NOT NULL"))
    for uid, val in rows.fetchall():
        new = convert(val, key)
        if new != val:
            conn.execute(
                sa.text("UPDATE users SET totp_secret = :v WHERE id = :i"), {"v": new, "i": uid}
            )


def _enc(val: str, key: bytes) -> str:
    try:
        decrypt_secret(val, key)
        return val  # already encrypted
    except InvalidToken:
        return encrypt_secret(val, key)


def _dec(val: str, key: bytes) -> str:
    try:
        return decrypt_secret(val, key)
    except InvalidToken:
        return val


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_pending_secret", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("two_factor_required_since", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "communities",
        sa.Column("require_2fa", sa.Text(), nullable=False, server_default="off"),
    )
    op.create_check_constraint(
        "communities_require_2fa_check",
        "communities",
        "require_2fa IN ('off','admins','everyone')",
    )
    op.create_table(
        "passkeys",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.func.gen_random_uuid()
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "community_id",
            UUID(as_uuid=True),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
            server_default=_COMMUNITY,
        ),
        sa.Column("credential_id", BYTEA(), nullable=False, unique=True),
        sa.Column("public_key", BYTEA(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transports", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("name", sa.Text(), nullable=False, server_default="Passkey"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("passkeys_user_idx", "passkeys", ["user_id"])
    # Unfinished enrolments (secret stored, never confirmed) are stale: drop them.
    op.execute("UPDATE users SET totp_secret = NULL WHERE NOT totp_enabled")
    _rewrite(_enc)


def downgrade() -> None:
    _rewrite(_dec)
    op.drop_index("passkeys_user_idx", table_name="passkeys")
    op.drop_table("passkeys")
    op.drop_constraint("communities_require_2fa_check", "communities", type_="check")
    op.drop_column("communities", "require_2fa")
    op.drop_column("users", "two_factor_required_since")
    op.drop_column("users", "totp_pending_secret")
