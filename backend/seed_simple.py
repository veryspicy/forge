import asyncio, sys, os, json
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/forge"
sys.path.insert(0, r"D:\codeRepo\forge\backend\src")

from forge.main.application import app
from forge.infrastructure.persistence.database import async_session_factory
from forge.infrastructure.persistence.models import ORMProduct, ORMRegion

async def main():
    async with async_session_factory() as session:
        # Region
        session.add(ORMRegion(code="na", name="North America", currency="USD", languages=["en"],
            tax_rate=8.25, tax_name="Sales Tax", payment_methods=["stripe"],
            shipping_methods=["standard","express"], is_active=True))
        session.add(ORMRegion(code="eu", name="Europe", currency="EUR", languages=["en","de","fr"],
            tax_rate=19.0, tax_name="VAT", payment_methods=["stripe"],
            shipping_methods=["standard","express"], is_active=True))

        # Product
        session.add(ORMProduct(sku="PET-FOOD-001", slug="premium-kibble-chicken",
            name="Premium Kibble - Chicken and Rice", description="High-protein dog food.",
            price=49.99, cost=22.00, category="FOOD", breed_groups=["DOG"],
            suitable_for={}, tags=["grain-free"], inventory=500,
            region_availability=["na","eu"], seo_keywords=["dog food"]))
        session.add(ORMProduct(sku="PET-TOY-001", slug="durable-chew-ring",
            name="Durable Chew Ring Blue", description="Rubber chew toy.",
            price=14.49, cost=5.50, category="TOYS", breed_groups=["DOG"],
            suitable_for={}, tags=["durable"], inventory=1200,
            region_availability=["na","eu"], seo_keywords=["dog toy"]))

        await session.commit()
        print("OK: 2 regions, 2 products")

asyncio.run(main())
