from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/callback/{callback_path:path}")
async def callback_zerodha(
    callback_path: str,
    request: Request,
    *,
    request_token: str | None = None,
    state: str | None = None,
    message: str | None = None,
):
    return {"status": "ok"}

client = TestClient(app)
response = client.get("/callback/some/path?status=error&message=Session+expired")
print(response.json())
