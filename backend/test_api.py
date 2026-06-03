import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"full_name": "Test User 2", "email": "test222@example.com", "password": "password123"}
        )
        print("Status:", response.status_code)
        print("Response:", response.text)

asyncio.run(test())
