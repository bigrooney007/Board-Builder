import os

import stripe
from dotenv import load_dotenv


load_dotenv()
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

CATALOG = [
    ("recruitment_97", "Board Recruitment — Execute It Yourself", 9700),
    ("recruitment_497", "Board Recruitment — Self-Guided System", 49700),
    ("reactivation_97", "Board Reactivation — Execute It Yourself", 9700),
    ("reactivation_497", "Board Reactivation — Self-Guided System", 49700),
    ("fundraising_activation_97", "Board Fundraising Activation — Execute It Yourself", 9700),
    ("fundraising_activation_497", "Board Fundraising Activation — Self-Guided System", 49700),
    ("recruit_with_rooney_997", "Recruit With Rooney", 99700),
    ("direct_board_recruitment_project", "Board Recruitment Project", 199850),
]


def ensure_tax_settings():
    settings = stripe.tax.Settings.retrieve()
    if settings.head_office and getattr(settings.head_office, "address", None):
        return
    stripe.tax.Settings.modify(
        head_office={"address": {
            "country": "US",
            "line1": "651 N Broad Street",
            "city": "Middletown",
            "state": "DE",
            "postal_code": "19709",
        }},
        defaults={"tax_behavior": "exclusive"},
    )


def product_for(stable_id: str, name: str):
    for product in stripe.Product.list(active=True).auto_paging_iter():
        if product.metadata.get("emergent_product_id") == stable_id:
            return product
    return stripe.Product.create(
        name=name,
        tax_code="txcd_10000000",
        metadata={"managed_by": "emergent", "emergent_product_id": stable_id},
    )


def ensure_catalog():
    ensure_tax_settings()
    prices = {}
    for lookup_key, name, amount in CATALOG:
        product = product_for(lookup_key, name)
        existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
        if existing and (existing[0].unit_amount != amount or existing[0].currency != "usd"):
            stripe.Price.modify(existing[0].id, active=False)
            existing = []
        price = existing[0] if existing else stripe.Price.create(
            product=product.id,
            unit_amount=amount,
            currency="usd",
            lookup_key=lookup_key,
            transfer_lookup_key=True,
        )
        prices[lookup_key] = price.id
    return prices


if __name__ == "__main__":
    for key, price_id in ensure_catalog().items():
        print(f"{key}={price_id}")