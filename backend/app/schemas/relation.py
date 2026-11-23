"""
@file relation.py
@brief Request/response models for relations.
"""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Kind = Literal["parent", "child", "spouse", "partner", "sibling", "friend", "other"]


class RelationCreate(BaseModel):
    """
    @brief Ask to link someone. ``kind`` is what the other person is to
           you ("Ruth is my parent"). Exactly one target.
    """

    to_user_id: UUID | None = None
    to_member_id: UUID | None = None
    kind: Kind
    label: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def _one_target(self) -> Self:
        """@brief One target; ``other`` needs a label, others drop it."""
        if (self.to_user_id is None) == (self.to_member_id is None):
            raise ValueError("Pick one person")
        self.label = (self.label or "").strip() or None
        if self.kind == "other" and self.label is None:
            raise ValueError("Say how you are related")
        if self.kind != "other":
            self.label = None
        return self


class RelationPerson(BaseModel):
    """@brief The other side of a relation."""

    id: UUID
    type: Literal["user", "household"]
    name: str
    username: str | None = None
    avatar_url: str | None = None
    memorial: bool = False


class RelationOut(BaseModel):
    """@brief One relation from the subject's point of view."""

    id: UUID
    status: Literal["pending", "confirmed"]
    kind: Kind
    label: str | None
    display: str
    direction: Literal["incoming", "outgoing"] | None = None
    person: RelationPerson
