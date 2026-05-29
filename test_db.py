import asyncio
from app.core.database import AsyncSessionLocal
from app.schemas.auth import UserCreate
from app.services.auth_service import register_user

async def test():
    try:
        async with AsyncSessionLocal() as db:
            payload = UserCreate(full_name="Test User", email="test3@example.com", password="password123")
            user = await register_user(db, payload)
            print("Success:", user.email)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
