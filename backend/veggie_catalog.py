"""Vegetable catalog and deterministic helpers for VeggieAI APIs."""

from __future__ import annotations

from typing import Any

SUPERMARKET_KEYS = ("ntuc", "giant", "coldStorage", "shengSiong")


VEGETABLE_CATALOG: dict[str, dict[str, Any]] = {
    "tomato": {
        "name": "Tomato",
        "scientificName": "Solanum lycopersicum",
        "category": "Fruit Vegetable",
        "description": "A red edible fruit from the nightshade family, commonly used in cooking.",
        "nutrients": ["Vitamin C", "Potassium", "Lycopene", "Vitamin K"],
        "prices": {"ntuc": 3.50, "giant": 3.20, "coldStorage": 3.95, "shengSiong": 3.10},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "5-7 days",
    },
    "carrot": {
        "name": "Carrot",
        "scientificName": "Daucus carota",
        "category": "Root Vegetable",
        "description": "A root vegetable typically orange in color, known for high beta-carotene.",
        "nutrients": ["Beta-carotene", "Fiber", "Vitamin K1", "Potassium"],
        "prices": {"ntuc": 2.80, "giant": 2.60, "coldStorage": 3.20, "shengSiong": 2.50},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "2-4 weeks",
    },
    "broccoli": {
        "name": "Broccoli",
        "scientificName": "Brassica oleracea var. italica",
        "category": "Cruciferous Vegetable",
        "description": "A green plant in the cabbage family with a large flowering head.",
        "nutrients": ["Vitamin C", "Vitamin K", "Iron", "Fiber"],
        "prices": {"ntuc": 4.20, "giant": 3.90, "coldStorage": 4.80, "shengSiong": 3.70},
        "unit": "per kg",
        "seasonality": "Oct-Apr",
        "storageLife": "3-5 days",
    },
    "cucumber": {
        "name": "Cucumber",
        "scientificName": "Cucumis sativus",
        "category": "Gourd Vegetable",
        "description": "A widely cultivated vine plant bearing elongated green fruits.",
        "nutrients": ["Vitamin K", "Potassium", "Magnesium", "Manganese"],
        "prices": {"ntuc": 2.50, "giant": 2.30, "coldStorage": 2.95, "shengSiong": 2.20},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "7-10 days",
    },
    "pepper": {
        "name": "Bell Pepper",
        "scientificName": "Capsicum annuum",
        "category": "Fruit Vegetable",
        "description": "A cultivar group of Capsicum annuum available in many colors.",
        "nutrients": ["Vitamin C", "Vitamin A", "Vitamin B6", "Folate"],
        "prices": {"ntuc": 5.80, "giant": 5.50, "coldStorage": 6.50, "shengSiong": 5.30},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "5-7 days",
    },
    "potato": {
        "name": "Potato",
        "scientificName": "Solanum tuberosum",
        "category": "Root Vegetable",
        "description": "A starchy tuberous crop from the perennial nightshade family.",
        "nutrients": ["Potassium", "Vitamin C", "Vitamin B6", "Fiber"],
        "prices": {"ntuc": 2.20, "giant": 2.00, "coldStorage": 2.60, "shengSiong": 1.90},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "2-3 months",
    },
    "onion": {
        "name": "Onion",
        "scientificName": "Allium cepa",
        "category": "Bulb Vegetable",
        "description": "A bulb vegetable and one of the most widely cultivated alliums.",
        "nutrients": ["Vitamin C", "Vitamin B6", "Folate", "Potassium"],
        "prices": {"ntuc": 2.90, "giant": 2.70, "coldStorage": 3.30, "shengSiong": 2.60},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "1-2 months",
    },
    "cabbage": {
        "name": "Cabbage",
        "scientificName": "Brassica oleracea var. capitata",
        "category": "Leafy Vegetable",
        "description": "A leafy green, red, or white biennial grown as an annual vegetable.",
        "nutrients": ["Vitamin K", "Vitamin C", "Fiber", "Manganese"],
        "prices": {"ntuc": 1.80, "giant": 1.60, "coldStorage": 2.10, "shengSiong": 1.50},
        "unit": "per kg",
        "seasonality": "Nov-Apr",
        "storageLife": "1-2 weeks",
    },
    "lettuce": {
        "name": "Lettuce",
        "scientificName": "Lactuca sativa",
        "category": "Leafy Vegetable",
        "description": "An annual plant of the daisy family, often grown as a leaf vegetable.",
        "nutrients": ["Vitamin A", "Vitamin K", "Folate", "Iron"],
        "prices": {"ntuc": 3.20, "giant": 2.90, "coldStorage": 3.70, "shengSiong": 2.80},
        "unit": "per head",
        "seasonality": "Year-round",
        "storageLife": "5-7 days",
    },
    "spinach": {
        "name": "Spinach",
        "scientificName": "Spinacia oleracea",
        "category": "Leafy Vegetable",
        "description": "A leafy green flowering plant native to central and western Asia.",
        "nutrients": ["Iron", "Calcium", "Vitamin A", "Vitamin C"],
        "prices": {"ntuc": 4.50, "giant": 4.20, "coldStorage": 5.10, "shengSiong": 4.00},
        "unit": "per kg",
        "seasonality": "Oct-Apr",
        "storageLife": "5-7 days",
    },
    "bean": {
        "name": "Bean",
        "scientificName": "Phaseolus vulgaris",
        "category": "Legume",
        "description": "Green bean pods commonly used in stir-fries, soups, and side dishes.",
        "nutrients": ["Fiber", "Vitamin C", "Folate", "Manganese"],
        "prices": {"ntuc": 3.90, "giant": 3.60, "coldStorage": 4.40, "shengSiong": 3.50},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "4-6 days",
    },
    "bitter_gourd": {
        "name": "Bitter_Gourd",
        "scientificName": "Momordica charantia",
        "category": "Gourd Vegetable",
        "description": "A nutrient-rich gourd with a distinct bitter flavor used in many Asian dishes.",
        "nutrients": ["Vitamin C", "Folate", "Fiber", "Potassium"],
        "prices": {"ntuc": 4.10, "giant": 3.80, "coldStorage": 4.80, "shengSiong": 3.70},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "4-6 days",
    },
    "brinjal": {
        "name": "Brinjal",
        "scientificName": "Solanum melongena",
        "category": "Fruit Vegetable",
        "description": "Also known as eggplant; versatile in curries, stews, and roasted dishes.",
        "nutrients": ["Fiber", "Manganese", "Vitamin B6", "Potassium"],
        "prices": {"ntuc": 3.70, "giant": 3.40, "coldStorage": 4.20, "shengSiong": 3.30},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "5-7 days",
    },
    "capsicum": {
        "name": "Capsicum",
        "scientificName": "Capsicum annuum",
        "category": "Fruit Vegetable",
        "description": "Sweet bell pepper available in green, red, yellow, and orange varieties.",
        "nutrients": ["Vitamin C", "Vitamin A", "Vitamin B6", "Folate"],
        "prices": {"ntuc": 5.80, "giant": 5.50, "coldStorage": 6.50, "shengSiong": 5.30},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "5-7 days",
    },
    "cauliflower_and_broccoli": {
        "name": "Cauliflower and Broccoli",
        "scientificName": "Brassica oleracea (varieties)",
        "category": "Cruciferous Vegetable",
        "description": "A combined leafy-flower class covering cauliflower and broccoli types.",
        "nutrients": ["Vitamin C", "Vitamin K", "Folate", "Fiber"],
        "prices": {"ntuc": 4.40, "giant": 4.10, "coldStorage": 5.00, "shengSiong": 3.90},
        "unit": "per kg",
        "seasonality": "Oct-Apr",
        "storageLife": "3-5 days",
    },
    "cucumber_and_bottle_gourd": {
        "name": "Cucumber and Bottle_Gourd",
        "scientificName": "Cucumis sativus / Lagenaria siceraria",
        "category": "Gourd Vegetable",
        "description": "A combined class for cucumber and bottle gourd vegetables.",
        "nutrients": ["Vitamin K", "Potassium", "Fiber", "Magnesium"],
        "prices": {"ntuc": 2.60, "giant": 2.40, "coldStorage": 3.00, "shengSiong": 2.30},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "7-10 days",
    },
    "pumpkin": {
        "name": "Pumpkin",
        "scientificName": "Cucurbita moschata",
        "category": "Gourd Vegetable",
        "description": "A dense orange-fleshed vegetable often used in soups and roasting.",
        "nutrients": ["Vitamin A", "Fiber", "Potassium", "Vitamin C"],
        "prices": {"ntuc": 3.20, "giant": 2.90, "coldStorage": 3.70, "shengSiong": 2.80},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "2-3 weeks",
    },
    "radish_and_carrot": {
        "name": "Radish and Carrot",
        "scientificName": "Raphanus sativus / Daucus carota",
        "category": "Root Vegetable",
        "description": "A combined root-vegetable class for radish and carrot families.",
        "nutrients": ["Fiber", "Vitamin C", "Potassium", "Folate"],
        "prices": {"ntuc": 2.90, "giant": 2.70, "coldStorage": 3.30, "shengSiong": 2.60},
        "unit": "per kg",
        "seasonality": "Year-round",
        "storageLife": "1-2 weeks",
    },
}


_SUPERMARKET_LOCATIONS = {
    "ntuc": ["Jurong Point", "Vivo City", "Tampines 1", "IMM"],
    "giant": ["Parkway Parade", "Tampines", "Ang Mo Kio Hub", "Westgate"],
    "coldStorage": ["Takashimaya", "Marina Square", "Paragon", "ION Orchard"],
    "shengSiong": ["Bedok North", "Yishun", "Clementi", "Hougang"],
}

_QUALITY_TIERS = (
    ("Standard", 0.90),
    ("Premium", 1.00),
    ("Organic", 1.15),
)

_UPDATED_MARKS = ("1h ago", "2h ago", "3h ago", "4h ago")

_ALIASES = {
    "bell pepper": "capsicum",
    "eggplant": "brinjal",
    "bitter gourd": "bitter_gourd",
    "cauliflower and broccoli": "cauliflower_and_broccoli",
    "cucumber and bottle gourd": "cucumber_and_bottle_gourd",
    "radish and carrot": "radish_and_carrot",
}


def normalize_vegetable_key(value: str) -> str:
    """Execute normalize vegetable key."""
    key = " ".join((value or "").strip().lower().replace("_", " ").split())
    if not key:
        return ""
    if key in VEGETABLE_CATALOG:
        return key
    if key in _ALIASES:
        return _ALIASES[key]

    compact = key.replace(" ", "")
    for known_key, details in VEGETABLE_CATALOG.items():
        known_compact = known_key.replace(" ", "")
        if compact == known_compact:
            return known_key
        if compact == details["name"].lower().replace(" ", ""):
            return known_key

    return key


def pick_vegetable_from_hash(file_sha256: str) -> str:
    """Execute pick vegetable from hash."""
    keys = sorted(VEGETABLE_CATALOG.keys())
    idx = int(file_sha256[:8], 16) % len(keys)
    return keys[idx]


def confidence_from_hash(file_sha256: str) -> float:
    """Execute confidence from hash."""
    whole = 80 + (int(file_sha256[8:10], 16) % 19)
    fraction = (int(file_sha256[10:12], 16) % 100) / 100.0
    return round(min(99.9, whole + fraction), 1)


def build_price_details(prices: dict[str, float]) -> dict[str, dict[str, Any]]:
    """Execute build price details."""
    details: dict[str, dict[str, Any]] = {}
    for market in SUPERMARKET_KEYS:
        base = float(prices[market])
        variations = []
        for i, (quality, multiplier) in enumerate(_QUALITY_TIERS):
            location = _SUPERMARKET_LOCATIONS[market][i % len(_SUPERMARKET_LOCATIONS[market])]
            last_updated = _UPDATED_MARKS[i % len(_UPDATED_MARKS)]
            variations.append(
                {
                    "price": round(base * multiplier, 2),
                    "quality": quality,
                    "location": location,
                    "lastUpdated": last_updated,
                }
            )
        details[market] = {
            "average": base,
            "variations": sorted(variations, key=lambda row: row["price"]),
        }
    return details


def serialize_catalog_item(item: dict[str, Any]) -> dict[str, Any]:
    """Execute serialize catalog item."""
    payload = dict(item)
    payload["prices"] = dict(item["prices"])
    payload["priceDetails"] = build_price_details(payload["prices"])
    return payload
