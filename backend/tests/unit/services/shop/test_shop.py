"""
@file test_shop.py
@brief Shop facts: product extraction, Amazon ASINs and API parsing, and
       when a wish's price follows the shop.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.services.shop import amazon
from app.services.shop.lookup import lookup_product
from app.services.shop.product import Product, extract_product, to_cents
from app.services.shop.refresh import ShopRefreshService, apply_price

LD = """<html><head>
<meta property="og:site_name" content="Target">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"BreadcrumbList"},
 {"@type":["Product"],"name":"Crayola Crayons, 64ct","image":["https://img.example/c.jpg"],
  "offers":[{"@type":"Offer","price":"4.99","priceCurrency":"usd"}]}]}</script>
</head></html>"""

META = """<meta content="Wooden train set" property="og:title">
<meta property='og:image' content='/img/train.png'>
<meta property="product:price:amount" content="1,249.50">
<meta property="product:price:currency" content="CAD">"""


def test_to_cents():
    assert to_cents("$8") == 800
    assert to_cents("1,299.99") == 129999
    assert to_cents(12.5) == 1250
    assert to_cents("free") is None
    assert to_cents(0) is None
    assert to_cents(True) is None


def test_json_ld_product_in_graph():
    p = extract_product(LD)
    assert (p.title, p.price_cents, p.currency, p.site_name) == (
        "Crayola Crayons, 64ct",
        499,
        "USD",
        "Target",
    )
    assert p.image_url == "https://img.example/c.jpg"


def test_meta_fallback_any_attribute_order():
    p = extract_product(META)
    assert (p.title, p.image_url, p.price_cents, p.currency) == (
        "Wooden train set",
        "/img/train.png",
        124950,
        "CAD",
    )


def test_aggregate_offer_and_broken_json():
    page = (
        '<script type="application/ld+json">{not json</script>'
        '<script type="application/ld+json">{"@type":"Product","name":"Bike",'
        '"offers":{"@type":"AggregateOffer","lowPrice":199,"priceCurrency":"EUR"}}</script>'
    )
    p = extract_product(page)
    assert (p.title, p.price_cents, p.currency) == ("Bike", 19900, "EUR")


@pytest.mark.parametrize(
    ("url", "asin"),
    [
        ("https://www.amazon.com/Crayola-Crayons/dp/B00000J0S3/ref=sr_1_1", "B00000J0S3"),
        ("https://amazon.co.uk/gp/product/b07fz8s74r?th=1", "B07FZ8S74R"),
        ("https://www.amazon.com/dp/B07FZ8S74R", "B07FZ8S74R"),
        ("https://www.amazon.com/s?k=crayons", None),
        ("https://amazon.evil.example/dp/B07FZ8S74R", None),
        ("https://www.target.com/p/B07FZ8S74R", None),
    ],
)
def test_asin_from_url(url, asin):
    assert amazon.asin_from_url(url) == asin


@pytest.mark.parametrize("root", ["itemResults", "itemsResult"])
def test_parse_items_either_root_and_image_fallback(root):
    body = {
        root: {
            "items": [
                {
                    "asin": "B07FZ8S74R",
                    "detailPageURL": "https://www.amazon.com/dp/B07FZ8S74R?tag=nx-20&linkCode=ogi",
                    "itemInfo": {"title": {"displayValue": "Echo Dot"}},
                    "images": {
                        "primary": {"large": None, "medium": {"url": "https://m.media/x.jpg"}}
                    },
                    "offersV2": {
                        "listings": [{"price": {"money": {"amount": 49.99, "currency": "USD"}}}]
                    },
                }
            ]
        }
    }
    p = amazon.parse_items(body)["B07FZ8S74R"]
    assert (p.title, p.image_url, p.price_cents, p.currency, p.site_name) == (
        "Echo Dot",
        "https://m.media/x.jpg",
        4999,
        "USD",
        "Amazon",
    )
    assert p.buy_url and "tag=nx-20" in p.buy_url


async def test_amazon_links_never_scraped_and_skipped_without_keys():
    s = Settings()
    with patch("app.services.shop.lookup.safe_get", AsyncMock()) as get:
        assert await lookup_product("https://www.amazon.com/dp/B07FZ8S74R", s) is None
    get.assert_not_awaited()


def _item(**kw):
    base = dict(
        id=uuid.uuid4(),
        kind="gift",
        price_cents=None,
        price_auto=False,
        url="https://shop.example/p",
        preview_id=None,
    )
    return SimpleNamespace(**{**base, **kw})


def test_apply_price_rules():
    prod = Product(price_cents=499, currency="USD")
    empty = _item()
    assert apply_price(empty, prod, "USD") and (empty.price_cents, empty.price_auto) == (499, True)
    typed = _item(price_cents=900)
    assert not apply_price(typed, prod, "USD") and typed.price_cents == 900
    following = _item(price_cents=600, price_auto=True)
    assert apply_price(following, prod, "USD") and following.price_cents == 499
    other_cur = _item()
    assert not apply_price(other_cur, Product(price_cents=499, currency="EUR"), "USD")
    fund = _item(kind="fund")
    assert not apply_price(fund, prod, "USD")


async def test_refresh_batches_amazon_and_stores_preview():
    a = _item(url="https://www.amazon.com/dp/B07FZ8S74R")
    b = _item(url="https://shop.example/crayons")
    items = AsyncMock()
    items.linked_for_refresh.return_value = [(a, "USD"), (b, "USD")]
    previews = AsyncMock()
    previews.upsert_shop.side_effect = lambda url, v: SimpleNamespace(id=uuid.uuid4())
    svc = ShopRefreshService(items, previews, Settings())
    with (
        patch(
            "app.services.shop.refresh.amazon.lookup",
            AsyncMock(
                return_value={"B07FZ8S74R": Product(title="Echo", price_cents=4999, currency="USD")}
            ),
        ) as lk,
        patch(
            "app.services.shop.refresh.lookup_product",
            AsyncMock(return_value=Product(title="Crayons", price_cents=499, currency="USD")),
        ),
    ):
        assert await svc.refresh() == 2
    lk.assert_awaited_once()
    assert lk.await_args.args[0] == ["B07FZ8S74R"]
    assert (a.price_cents, b.price_cents) == (4999, 499)
    assert a.preview_id and b.preview_id


def test_hostile_page_parses_in_linear_time():
    import time

    page = '<script type="application/ld+json">' * 50_000 + "<meta content=" * 100_000
    page += "</script>"  # one far close tag must not be rescanned per open tag
    t = time.perf_counter()
    assert extract_product(page).title is None
    assert time.perf_counter() - t < 2


async def test_failed_lookup_is_stamped_and_batch_continues():
    bad = _item(url="https://broken.example/x")
    good = _item(url="https://shop.example/crayons")
    items = AsyncMock()
    items.linked_for_refresh.return_value = [(bad, "USD"), (good, "USD")]
    previews = AsyncMock()
    previews.upsert_shop.side_effect = lambda url, v: SimpleNamespace(id=uuid.uuid4())
    svc = ShopRefreshService(items, previews, Settings())
    lookup = AsyncMock(side_effect=[RuntimeError("boom"), Product(title="C", price_cents=499)])
    with patch("app.services.shop.refresh.lookup_product", lookup):
        assert await svc.refresh() == 1
    first = previews.upsert_shop.await_args_list[0].args
    assert first == ("https://broken.example/x", {"title": "", "fetch_error": True})
    assert bad.preview_id and good.price_cents == 499
