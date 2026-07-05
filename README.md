# catalog-enrichment-skill

> **GenPark AI Agent Skill** -- Auto-enrich product catalogs by detecting missing attributes, generating descriptions, inferring categories, and scoring completeness.

## Features

- Category inference from product name and description text
- Auto-tag generation per category (beauty, fitness, electronics, fashion, home, food, toys, sports)
- Description generation from templates per category
- Price normalization (removes $, commas, converts to float)
- Field completeness scoring (weighted by field importance)
- Catalog health grade: A/B/C/D
- Issues report for products needing manual attention

## Quick Start

```python
from client import CatalogEnrichmentClient

client = CatalogEnrichmentClient()
result = client.enrich(
    products=[{"id":"P1","name":"Vitamin C Serum","price":35,"description":"","category":"","tags":[],"images":[]}],
)
print(result["catalog_health"])
for p in result["enriched_products"]:
    print(f"{p['name']}: {p['_completeness_score']}% complete | Changes: {p['_changes_made']}")
```

## Installation

```bash
python example_usage.py  # No external dependencies
```

---
Built by [GenPark](https://genpark.ai) | [alphaparkinc](https://github.com/alphaparkinc)
