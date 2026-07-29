import asyncio, sys, os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/forge"
sys.path.insert(0, r"D:\codeRepo\forge\backend\src")

from forge.main.application import app
from forge.infrastructure.persistence.database import async_session_factory
from forge.infrastructure.persistence.models import ORMProduct, ORMRegion


async def main():
    async with async_session_factory() as session:
        products = [
            ORMProduct(sku="PET-FOOD-001", slug="premium-kibble-chicken", name="Premium Kibble - Chicken and Rice", description="High-protein kibble with real chicken, brown rice, and vegetables.", price=49.99, cost=22.00, category="FOOD", breed_groups=["DOG"], suitable_for={}, tags=["grain-free","high-protein","chicken"], inventory=500, region_availability=["na","eu"], seo_keywords=["dog food","kibble","chicken"]),
            ORMProduct(sku="PET-TOY-001", slug="durable-chew-ring", name="Durable Chew Ring Blue", description="Non-toxic natural rubber chew ring for aggressive chewers.", price=14.49, cost=5.50, category="TOYS", breed_groups=["DOG"], suitable_for={}, tags=["durable","chew","rubber"], inventory=1200, region_availability=["na","eu"], seo_keywords=["dog toy","chew ring"]),
            ORMProduct(sku="PET-TREAT-001", slug="salmon-training-bites", name="Salmon Training Bites", description="Soft bite-sized salmon treats rich in Omega-3. Great for training.", price=9.99, cost=3.20, category="FOOD", breed_groups=["DOG","CAT"], suitable_for={}, tags=["salmon","omega-3","training","soft"], inventory=800, region_availability=["na","eu"], seo_keywords=["dog treats","salmon","training"]),
            ORMProduct(sku="PET-BED-001", slug="orthopedic-memory-foam-bed", name="Orthopedic Memory Foam Bed Large", description="Therapeutic memory foam bed for senior dogs. Waterproof liner.", price=89.99, cost=38.00, category="FURNITURE", breed_groups=["DOG"], suitable_for={}, tags=["orthopedic","memory-foam","waterproof","senior"], inventory=200, region_availability=["na","eu"], seo_keywords=["dog bed","orthopedic","senior dog"]),
            ORMProduct(sku="PET-GROOM-001", slug="slicker-brush-pro", name="Slicker Brush Pro Self-Cleaning", description="Self-cleaning slicker brush with fine bent wires.", price=19.99, cost=7.00, category="GROOMING", breed_groups=["DOG","CAT"], suitable_for={}, tags=["slicker","self-cleaning","grooming"], inventory=600, region_availability=["na","eu"], seo_keywords=["dog brush","slicker","grooming"]),
            ORMProduct(sku="PET-COLLAR-001", slug="reflective-adjustable-collar", name="Reflective Adjustable Collar Orange", description="High-visibility reflective collar with quick-release buckle.", price=12.99, cost=4.50, category="ACCESSORIES", breed_groups=["DOG"], suitable_for={}, tags=["reflective","adjustable","safety"], inventory=900, region_availability=["na","eu"], seo_keywords=["dog collar","reflective","safety"]),
            ORMProduct(sku="PET-HEALTH-001", slug="joint-support-chews", name="Joint Support Chews Glucosamine", description="Veterinary-grade glucosamine and chondroitin chews.", price=34.99, cost=14.00, category="HEALTH", breed_groups=["DOG"], suitable_for={}, tags=["glucosamine","chondroitin","joint","senior"], inventory=350, region_availability=["na","eu"], seo_keywords=["dog supplements","glucosamine","joint health"]),
            ORMProduct(sku="PET-FOOD-002", slug="puppy-growth-formula", name="Puppy Growth Formula Lamb and Sweet Potato", description="Complete nutrition for growing puppies. DHA for brain development.", price=54.99, cost=25.00, category="FOOD", breed_groups=["DOG"], suitable_for={}, tags=["puppy","lamb","DHA","growth"], inventory=400, region_availability=["na","eu"], seo_keywords=["puppy food","lamb","growth"]),
            ORMProduct(sku="PET-CAT-FOOD-001", slug="grain-free-cat-salmon", name="Grain-Free Cat Food Wild Salmon", description="Protein-rich grain-free formula for indoor cats.", price=39.99, cost=18.00, category="FOOD", breed_groups=["CAT"], suitable_for={}, tags=["grain-free","salmon","indoor","cat"], inventory=350, region_availability=["na","eu"], seo_keywords=["cat food","salmon","grain-free"]),
            ORMProduct(sku="PET-CAT-LITTER-001", slug="clumping-odor-lock-litter", name="Clumping Odor-Lock Litter Unscented", description="Low-dust clumping litter with activated charcoal.", price=22.99, cost=9.00, category="LITTER", breed_groups=["CAT"], suitable_for={}, tags=["clumping","odor-control","low-dust"], inventory=600, region_availability=["na","eu"], seo_keywords=["cat litter","clumping","odor control"]),
        ]
        session.add_all(products)
        region = ORMRegion(code="me", name="Middle East", currency="AED", languages=["en","ar"], tax_rate=5.0, tax_name="VAT", payment_methods=["stripe"], shipping_methods=["standard"], is_active=True, i18n={"direction":"rtl"})
        session.add(region)
        await session.commit()
        n = len(products)
        print(f"OK: {n} products, 1 region added")

asyncio.run(main())
