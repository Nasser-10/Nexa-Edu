import os
import sys
import asyncio

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from sqlalchemy import select

from app.core.database import engine, AsyncSessionLocal, Base
from app.core.security import get_password_hash
from app.models.schema import User, UserRole, Category, Skill

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Seed Categories
        res = await db.execute(select(Category))
        categories = res.scalars().all()
        if not categories:
            cat1 = Category(name="البرمجة والتطوير", slug="programming", icon="code")
            cat2 = Category(name="الثانوية العامة واللغات", slug="high-school", icon="book-open")
            cat3 = Category(name="الذكاء الاصطناعي", slug="ai-ml", icon="cpu")
            cat4 = Category(name="المهارات والبيزنس", slug="business", icon="briefcase")
            db.add_all([cat1, cat2, cat3, cat4])
            await db.commit()
            print("[SEED] Standard Categories initialized.")

        # Seed foundational skills used by the Learning Intelligence layer
        skill_res = await db.execute(select(Skill))
        if not skill_res.scalars().first():
            skills = [
                ("Python", "python", "Programming"),
                ("Machine Learning", "machine-learning", "AI"),
                ("Deep Learning", "deep-learning", "AI"),
                ("NLP", "nlp", "AI"),
                ("Computer Vision", "computer-vision", "AI"),
                ("SQL", "sql", "Data"),
                ("FastAPI", "fastapi", "Backend"),
                ("Docker", "docker", "DevOps"),
                ("Cloud", "cloud", "DevOps"),
                ("Communication", "communication", "Soft Skills"),
            ]
            db.add_all([Skill(name=n, slug=slug, category=cat) for n, slug, cat in skills])
            await db.commit()
            print("[SEED] Foundational learning skills initialized.")

        # Seed ONLY 1 Super Admin user (Zero demo students & Zero demo courses)
        res = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = res.scalar_one_or_none()
        if not admin:
            admin_user = User(
                email="admin@platform.com",
                password_hash=get_password_hash("Admin@123456"),
                full_name="المدير العام للمنصة",
                role=UserRole.ADMIN,
                is_teacher_approved=True
            )
            db.add(admin_user)
            await db.commit()
            print("[SEED] Platform Super Admin initialized: admin@platform.com / Admin@123456")

if __name__ == "__main__":
    print("[INIT] Initializing Production Ready Clean Database...")
    asyncio.run(seed_data())
    print("[START] Starting AI-Powered Educational Marketplace Server on http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
