#!/usr/bin/env python3
"""
@file create_admin.py
@brief Bootstrap an admin user for a fresh Nexara instance.

Usage:
    uv run python scripts/create_admin.py \\
        --username user1 --email user1@example.com \\
        --password 'YourSecureP@ss1'

All flags are optional and fall back to interactive prompts when omitted.
The script is idempotent -- if the username or email already exists it
prints a message and exits without error.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User


async def _user_exists(session: AsyncSession, username: str, email: str) -> str | None:
    """
    @brief Check whether a user with the given username or email already exists.
    @return A human-readable reason string, or None if no conflict.
    """
    row = (
        await session.execute(
            select(User.username, User.email).where(
                (User.username == username) | (User.email == email)
            )
        )
    ).first()

    if row is None:
        return None
    if row.username == username:
        return f"username '{username}'"
    return f"email '{email}'"


async def create_admin(
    username: str,
    email: str,
    password: str,
    display_name: str | None = None,
) -> None:
    """
    @brief Insert an admin user into the database.

    @param username  Unique login name.
    @param email     Unique email address.
    @param password  Plaintext password (will be bcrypt-hashed).
    @param display_name  Optional display name (defaults to username).
    """
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        conflict = await _user_exists(session, username, email)
        if conflict:
            print(f"[skip] User with {conflict} already exists.")
            await engine.dispose()
            return

        community_id = uuid.UUID(settings.COMMUNITY_ID)
        user = User(
            community_id=community_id,
            email=email,
            username=username,
            display_name=display_name or username,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print("[ok] Admin user created:")
        print(f"     id:       {user.id}")
        print(f"     username: {user.username}")
        print(f"     email:    {user.email}")
        print(f"     role:     {user.role}")

    await engine.dispose()


def _parse_args() -> argparse.Namespace:
    """@brief Parse CLI arguments with interactive fallback for missing values."""
    parser = argparse.ArgumentParser(
        description="Create a Nexara admin user (idempotent).",
    )
    parser.add_argument("--username", help="Login username")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--password", help="Plaintext password (prompted if omitted)")
    parser.add_argument("--display-name", help="Display name (defaults to username)")
    args = parser.parse_args()

    if not args.username:
        args.username = input("Username: ").strip()
    if not args.email:
        args.email = input("Email: ").strip()
    if not args.password:
        args.password = getpass.getpass("Password: ")

    if len(args.password) < 12:
        print("[error] Password must be at least 12 characters.", file=sys.stderr)
        sys.exit(1)

    return args


def main() -> None:
    """@brief Entry point -- parse args and run the async admin creation."""
    args = _parse_args()
    asyncio.run(
        create_admin(
            username=args.username,
            email=args.email,
            password=args.password,
            display_name=args.display_name,
        )
    )


if __name__ == "__main__":
    main()
