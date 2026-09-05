import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class Product(BaseModel):
    id: str
    name: str
    category: str
    description: str
    price: float           # Selling price in INR
    cost_price: float      # Merchant base cost in INR
    stock: int
    rating: float
    specs: Dict[str, Any]
    synergies: List[str]   # Compatible SKUs for dynamic bundling upsell
    schema_org: Dict[str, Any] # JSON-LD schema for UAP discovery

INITIAL_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "SKU-KB-01",
        "name": "ApexPro Mechanical Keyboard (Hot-swappable)",
        "category": "Peripherals",
        "description": "75% Wireless mechanical keyboard with pre-lubed tactile switches and RGB backlighting.",
        "price": 4999.0,
        "cost_price": 3200.0,
        "stock": 14,
        "rating": 4.8,
        "specs": {"connectivity": "Tri-mode 2.4G/BT/USB-C", "battery": "4000mAh", "switches": "Gateron Brown"},
        "synergies": ["SKU-WR-01", "SKU-KC-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "ApexPro Mechanical Keyboard",
            "sku": "SKU-KB-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 4999.0, "availability": "https://schema.org/InStock"}
        }
    },
    {
        "id": "SKU-WR-01",
        "name": "ErgoRest Memory Foam Wrist Rest",
        "category": "Accessories",
        "description": "Premium cooling-gel infused memory foam wrist pad for 75% and TKL keyboards.",
        "price": 999.0,
        "cost_price": 450.0,
        "stock": 35,
        "rating": 4.7,
        "specs": {"material": "Cooling Gel Memory Foam", "length": "32cm", "anti_slip": True},
        "synergies": ["SKU-KB-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "ErgoRest Memory Foam Wrist Rest",
            "sku": "SKU-WR-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 999.0, "availability": "https://schema.org/InStock"}
        }
    },
    {
        "id": "SKU-HP-01",
        "name": "SonicShield Pro ANC Headphones",
        "category": "Audio",
        "description": "Hybrid Active Noise Cancelling over-ear headphones with 45mm drivers and LDAC codec support.",
        "price": 6499.0,
        "cost_price": 4100.0,
        "stock": 8,
        "rating": 4.9,
        "specs": {"anc_depth": "42dB", "battery_life": "60 Hours", "codecs": ["LDAC", "AAC", "SBC"]},
        "synergies": ["SKU-CH-01", "SKU-HC-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "SonicShield Pro ANC Headphones",
            "sku": "SKU-HP-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 6499.0, "availability": "https://schema.org/InStock"}
        }
    },
    {
        "id": "SKU-CH-01",
        "name": "VoltFast 65W GaN Fast Charger",
        "category": "Power",
        "description": "Ultra-compact 3-port GaN fast charger with 2x USB-C PD 3.0 and 1x USB-A.",
        "price": 1899.0,
        "cost_price": 1050.0,
        "stock": 20,
        "rating": 4.6,
        "specs": {"ports": "2x Type-C, 1x Type-A", "output": "65W Max", "tech": "GaN III"},
        "synergies": ["SKU-HP-01", "SKU-KB-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "VoltFast 65W GaN Fast Charger",
            "sku": "SKU-CH-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 1899.0, "availability": "https://schema.org/InStock"}
        }
    },
    {
        "id": "SKU-MS-01",
        "name": "GlideMaster Wireless Ergonomic Mouse",
        "category": "Peripherals",
        "description": "57-degree vertical ergonomic mouse with silent switches and customizable DPI.",
        "price": 2499.0,
        "cost_price": 1400.0,
        "stock": 25,
        "rating": 4.5,
        "specs": {"dpi": "4000 DPI", "angle": "57 degrees vertical", "battery": "AA Battery 18 months"},
        "synergies": ["SKU-KB-01", "SKU-MP-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "GlideMaster Wireless Ergonomic Mouse",
            "sku": "SKU-MS-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 2499.0, "availability": "https://schema.org/InStock"}
        }
    },
    {
        "id": "SKU-MP-01",
        "name": "NovaDesk Extended Desk Mat (900x400mm)",
        "category": "Accessories",
        "description": "Water-resistant stitched-edge micro-woven cloth mousepad with anti-slip rubber base.",
        "price": 799.0,
        "cost_price": 300.0,
        "stock": 50,
        "rating": 4.8,
        "specs": {"size": "900 x 400 x 4mm", "surface": "Micro-weave cloth", "stitched_edges": True},
        "synergies": ["SKU-KB-01", "SKU-MS-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "NovaDesk Extended Desk Mat",
            "sku": "SKU-MP-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 799.0, "availability": "https://schema.org/InStock"}
        }
    },
    {
        "id": "SKU-HC-01",
        "name": "Hardshell Protective Headphone Case",
        "category": "Accessories",
        "description": "Shockproof EVA travel case with cable organizer mesh pouch for over-ear headphones.",
        "price": 699.0,
        "cost_price": 280.0,
        "stock": 18,
        "rating": 4.6,
        "specs": {"material": "EVA Hard Shell + Velvet interior", "waterproof": True},
        "synergies": ["SKU-HP-01"],
        "schema_org": {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "Hardshell Protective Headphone Case",
            "sku": "SKU-HC-01",
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": 699.0, "availability": "https://schema.org/InStock"}
        }
    }
]

class CatalogManager:
    def __init__(self):
        self.products: Dict[str, Product] = {
            item["id"]: Product(**item) for item in INITIAL_CATALOG
        }

    def get_all(self) -> List[Product]:
        return list(self.products.values())

    def get_by_id(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def search(self, query: str = "", max_price: Optional[float] = None) -> List[Product]:
        results = []
        q_lower = query.lower()
        for p in self.products.values():
            if max_price and p.price > max_price:
                continue
            if not query or (
                q_lower in p.name.lower() or 
                q_lower in p.category.lower() or 
                q_lower in p.description.lower()
            ):
                results.append(p)
        return results

    def get_uap_catalog_manifest(self) -> Dict[str, Any]:
        """NPCI UAP compliant Agent-Readable Catalog manifest."""
        return {
            "protocol": "NPCI-UAP-v1.0",
            "merchant_id": "MERCHANT_RAZORUAP_001",
            "currency": "INR",
            "supported_actions": [
                "uap:browse",
                "uap:request_quote",
                "uap:negotiate_bundle",
                "uap:gated_checkout"
            ],
            "catalog_count": len(self.products),
            "items": [(p.model_dump() if hasattr(p, "model_dump") else p.dict()) for p in self.products.values()]
        }

    def reserve_stock(self, product_id: str, quantity: int = 1) -> bool:
        p = self.products.get(product_id)
        if not p or p.stock < quantity:
            return False
        p.stock -= quantity
        return True

    def release_stock(self, product_id: str, quantity: int = 1):
        p = self.products.get(product_id)
        if p:
            p.stock += quantity

catalog_manager = CatalogManager()
