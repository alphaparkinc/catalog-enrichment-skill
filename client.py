"""
catalog-enrichment-skill: Client SDK
Auto-enrich product catalogs with missing attributes, inferred tags, and completeness scoring.
"""
from __future__ import annotations
import re
from typing import Optional

REQUIRED_FIELDS_DEFAULT = ["name", "description", "price", "category", "tags", "images"]

CATEGORY_KEYWORDS = {
    "beauty":     ["serum", "cream", "moisturizer", "sunscreen", "cleanser", "toner", "mask", "spf", "vitamin c", "retinol", "skincare", "makeup", "lipstick", "foundation"],
    "fitness":    ["yoga", "gym", "workout", "protein", "supplement", "resistance", "dumbbell", "kettlebell", "mat", "band", "running", "athletic"],
    "electronics":["wireless", "bluetooth", "usb", "charger", "earbuds", "speaker", "phone", "laptop", "tablet", "smart", "led", "hdmi"],
    "fashion":    ["shirt", "dress", "pants", "jeans", "jacket", "coat", "shoes", "sneakers", "boots", "bag", "handbag", "wallet", "scarf"],
    "home":       ["pillow", "blanket", "candle", "lamp", "storage", "organizer", "curtain", "rug", "towel", "kitchen", "cookware", "pot"],
    "food":       ["organic", "snack", "coffee", "tea", "chocolate", "protein bar", "supplement", "vitamin", "gummies", "powder", "mix"],
    "toys":       ["toy", "game", "puzzle", "board game", "lego", "doll", "action figure", "educational", "kids", "children"],
    "sports":     ["ball", "racket", "helmet", "gloves", "jersey", "cleats", "swimming", "cycling", "hiking", "camping"],
}

TAG_LIBRARY = {
    "beauty":     ["skincare", "beauty", "personal-care", "anti-aging", "hydrating", "natural", "vegan", "cruelty-free"],
    "fitness":    ["fitness", "workout", "gym", "health", "wellness", "activewear", "performance"],
    "electronics":["tech", "gadgets", "wireless", "smart-home", "productivity", "entertainment"],
    "fashion":    ["style", "fashion", "trendy", "wardrobe", "outfit", "accessories"],
    "home":       ["home-decor", "lifestyle", "cozy", "organization", "comfort"],
    "food":       ["food", "nutrition", "healthy", "organic", "snacks", "beverages"],
    "toys":       ["toys", "kids", "educational", "fun", "games", "children"],
    "sports":     ["sports", "outdoor", "adventure", "performance", "athletics"],
    "default":    ["product", "quality", "lifestyle", "value"],
}

DESCRIPTION_TEMPLATES = {
    "beauty":     "Experience the power of {name} -- a premium skincare solution designed to nourish, protect, and transform your skin. Formulated with high-quality ingredients for visible results.",
    "fitness":    "Elevate your workout with {name}. Built for performance, comfort, and durability to help you achieve your fitness goals every day.",
    "electronics":"{name} delivers cutting-edge technology designed for modern life. Enjoy seamless connectivity, superior performance, and sleek design.",
    "fashion":    "Elevate your style with {name}. Crafted for comfort and designed to impress, it is the perfect addition to any wardrobe.",
    "home":       "Transform your living space with {name}. Thoughtfully designed to bring beauty, comfort, and functionality to your home.",
    "food":       "Discover the taste and nutrition of {name} -- made with quality ingredients to fuel your day and delight your senses.",
    "default":    "{name} is a high-quality product designed to meet your everyday needs. Built to last and crafted with care.",
}

FIELD_WEIGHTS = {
    "name": 20, "description": 20, "price": 15, "category": 15,
    "tags": 10, "images": 10, "brand": 5, "sku": 3, "weight": 2,
}


class CatalogEnrichmentClient:
    """
    SDK for auto-enriching e-commerce product catalogs.
    Detects missing fields, infers categories and tags, generates descriptions,
    and scores completeness.
    """

    def enrich(
        self,
        products: list[dict],
        required_fields: Optional[list[str]] = None,
    ) -> dict:
        """
        Enrich a product catalog.

        Args:
            products:        List of product dicts.
            required_fields: Fields required for a complete product record.

        Returns:
            dict with enriched_products, catalog_health, issues
        """
        required = required_fields or REQUIRED_FIELDS_DEFAULT
        enriched = []
        issues = []

        for product in products:
            p = dict(product)
            changes = []

            # Infer category if missing
            if not p.get("category"):
                inferred = self._infer_category(p.get("name", "") + " " + p.get("description", ""))
                p["category"] = inferred
                p["_category_inferred"] = True
                changes.append("category inferred")

            cat = str(p.get("category", "default")).lower()

            # Infer tags if missing or empty
            if not p.get("tags"):
                p["tags"] = TAG_LIBRARY.get(cat, TAG_LIBRARY["default"])[:5]
                changes.append("tags generated")

            # Generate description if missing or too short
            desc = str(p.get("description", ""))
            if len(desc) < 30:
                tmpl = DESCRIPTION_TEMPLATES.get(cat, DESCRIPTION_TEMPLATES["default"])
                p["description"] = tmpl.format(name=p.get("name", "This product"))
                changes.append("description generated")

            # Normalize price
            if p.get("price") and not isinstance(p["price"], (int, float)):
                try:
                    p["price"] = float(str(p["price"]).replace("$", "").replace(",", ""))
                    changes.append("price normalized")
                except ValueError:
                    pass

            # Completeness score
            score = self._completeness_score(p, required)
            p["_completeness_score"] = score
            p["_changes_made"] = changes
            p["_missing_fields"] = [f for f in required if not p.get(f)]

            if p["_missing_fields"]:
                issues.append({
                    "product_id": p.get("id", "unknown"),
                    "name": p.get("name", ""),
                    "missing": p["_missing_fields"],
                    "completeness": score,
                })

            enriched.append(p)

        # Catalog health
        scores = [p["_completeness_score"] for p in enriched]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        critical = [p for p in enriched if p["_completeness_score"] < 50]

        catalog_health = {
            "total_products": len(products),
            "avg_completeness_score": avg_score,
            "fully_complete": sum(1 for s in scores if s == 100),
            "needs_attention": len([s for s in scores if s < 70]),
            "critical_incomplete": len(critical),
            "health_grade": "A" if avg_score >= 90 else "B" if avg_score >= 75 else "C" if avg_score >= 60 else "D",
        }

        return {
            "enriched_products": enriched,
            "catalog_health": catalog_health,
            "issues": sorted(issues, key=lambda x: x["completeness"])[:20],
        }

    @staticmethod
    def _infer_category(text: str) -> str:
        text = text.lower()
        scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            scores[cat] = sum(1 for kw in keywords if kw in text)
        best = max(scores, key=lambda k: scores[k])
        return best if scores[best] > 0 else "general"

    @staticmethod
    def _completeness_score(product: dict, required: list[str]) -> int:
        total_weight = sum(FIELD_WEIGHTS.get(f, 5) for f in required)
        earned = sum(FIELD_WEIGHTS.get(f, 5) for f in required if product.get(f))
        return round(earned / max(total_weight, 1) * 100)
