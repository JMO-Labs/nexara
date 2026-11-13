"""Intentionally broken plugin used by contract tester tests."""

import requests
from fastapi import APIRouter

from app.models.post import Post
from app.services import event_service

router = APIRouter()
API_KEY = "xxxxxxxxxxxx"  # low entropy placeholder


async def leak(ctx):
    requests.get("https://example.com")
    await ctx.notify(None, "system", {})
    return Post, event_service
