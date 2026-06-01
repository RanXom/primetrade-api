"""
Seed script — creates the initial admin user.

Usage:
    python scripts/seed.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal, create_tables
from app.services.user_service import create_admin_user, get_user_by_email


async def seed():
    print("🌱 Running seed...")
    await create_tables()

    async with AsyncSessionLocal() as session:
        admin_email = "admin@taskflow.dev"
        existing = await get_user_by_email(session, admin_email)
        if existing:
            print(f"✅ Admin user already exists: {admin_email}")
            return

        admin = await create_admin_user(
            session,
            email=admin_email,
            username="admin",
            password="Admin1234!",
            full_name="System Administrator",
        )
        await session.commit()
        print(f"✅ Admin user created:")
        print(f"   Email   : {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   Password: Admin1234!")
        print(f"   Role    : {admin.role}")
        print()
        print("⚠️  Change the admin password immediately in production!")


if __name__ == "__main__":
    asyncio.run(seed())
