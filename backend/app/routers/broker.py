"""
Broker router – connect / disconnect / sync broker accounts.
Supports multiple routing patterns to align with frontend API requests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import cache_set, cache_get, cache_delete
from app.core.security import encrypt_token, generate_state
from app.integrations.angelone import AngelOneClient
from app.integrations.binance import BinanceClient
from app.integrations.zerodha import ZerodhaClient
from app.models.broker import BrokerConnection, BrokerName
from app.models.user import User
from app.schemas.broker import (
    BrokerConnectRequest,
    BrokerConnectionResponse,
)
from app.services.auth_service import get_current_user
from app.services.portfolio_service import sync_broker_holdings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/broker", tags=["Broker Connections"])


# ── Zerodha OAuth flow ──────────────────────────────────────────────────


@router.post("/connect/zerodha", response_model=BrokerConnectionResponse | dict)
@router.post("/zerodha/connect", response_model=BrokerConnectionResponse | dict)
async def connect_zerodha(
    request: Request,
    payload: BrokerConnectRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectionResponse | dict:
    """Connect Zerodha account using direct credentials or return OAuth login URL."""
    creds = payload.credentials if payload else {}
    api_key = creds.get("api_key") or creds.get("apiKey")
    api_secret = creds.get("api_secret") or creds.get("apiSecret")
    access_token = creds.get("access_token") or creds.get("accessToken")
    
    if api_key and access_token:
        # Bypass OAuth, connect directly
        client = ZerodhaClient(access_token=access_token, api_key=api_key, api_secret=api_secret)
        try:
            profile = await client.get_profile()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to authenticate with Zerodha using provided credentials. Please check your API Key and Access Token. Error: {e}",
            )
        
        connection = BrokerConnection(
            user_id=current_user.id,
            broker_name=BrokerName.zerodha,
            encrypted_access_token=encrypt_token(access_token),
            broker_user_id=profile.get("broker_user_id"),
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(connection)
        await db.flush()
        
        # Sync holdings immediately
        try:
            await sync_broker_holdings(db, current_user.id, connection.id)
        except Exception as e:
            logger.error(f"Failed to sync Zerodha holdings on connection: {e}")
            
        await db.refresh(connection)
        return BrokerConnectionResponse.model_validate(connection)

    # Fallback to OAuth flow if no credentials provided
    state = generate_state()
    origin = request.headers.get("origin")
    if origin:
        await cache_set(f"zerodha_origin:{state}", origin, ttl=600)
    
    await cache_set(f"zerodha_state:{state}", str(current_user.id), ttl=600)
    callback_token = secrets.token_urlsafe(32)
    await cache_set(f"zerodha_callback:{callback_token}", str(current_user.id), ttl=600)
    if api_key:
        await cache_set(f"zerodha_api_key:{callback_token}", api_key, ttl=600)
        await cache_set(f"zerodha_api_key:{state}", api_key, ttl=600)
    if api_secret:
        await cache_set(f"zerodha_secret:{callback_token}", api_secret, ttl=600)
        await cache_set(f"zerodha_secret:{state}", api_secret, ttl=600)
    try:
        client = ZerodhaClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zerodha login is not configured on this deployment. Set KITE_API_KEY and KITE_API_SECRET on Render, or enable KITE_SIMULATOR_MODE for local testing.",
        ) from exc
    login_url = client.get_login_url()
    # Note: we append state but Zerodha may not echo it back; callback handles both cases
    login_url_with_state = f"{login_url}&state={state}"
    response = JSONResponse(
        {
            "login_url": login_url_with_state,
            "loginUrl": login_url_with_state,
            "redirect_url": login_url_with_state,
            "state": state,
            "callback_token": callback_token,
        }
    )
    response.set_cookie(
        key="zerodha_callback_token",
        value=callback_token,
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/callback/{callback_path:path}", response_model=BrokerConnectionResponse | dict)
async def callback_zerodha(
    callback_path: str,
    request: Request,
    request_token: str = Query(..., description="The request token from Kite"),
    state: str | None = Query(default=None, description="OAuth state token"),
    callback_token: str | None = Query(default=None, description="Internal callback token"),
    db: AsyncSession = Depends(get_db),
) -> BrokerConnectionResponse | dict:
    """Handle the OAuth callback from Zerodha, store encrypted token and sync."""
    if callback_path != "zerodha":
        raise HTTPException(status_code=400, detail="Unsupported broker callback")

    lookup_tokens = [
        callback_token,
        state,
        request.cookies.get("zerodha_callback_token"),
        request.query_params.get("state"),
        request.query_params.get("callback_token"),
    ]

    user_id: uuid.UUID | None = None
    api_key: str | None = None
    api_secret: str | None = None

    for token in [token for token in lookup_tokens if token]:
        cached_user_id = await cache_get(f"zerodha_callback:{token}") or await cache_get(f"zerodha_state:{token}")
        if cached_user_id:
            user_id = uuid.UUID(str(cached_user_id))
            api_key = await cache_get(f"zerodha_api_key:{token}") or api_key
            api_secret = await cache_get(f"zerodha_secret:{token}") or api_secret
            break

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to resolve Zerodha callback session. Please restart the connection flow.",
        )

    client = ZerodhaClient(api_key=api_key, api_secret=api_secret)
    try:
        access_token = await client.handle_callback(request_token)
        profile = await client.get_profile()
    except Exception as e:
        logger.error(f"Failed to exchange Zerodha token: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to connect to Zerodha: {e}")

    connection = BrokerConnection(
        user_id=user_id,
        broker_name=BrokerName.zerodha,
        encrypted_access_token=encrypt_token(access_token),
        broker_user_id=profile.get("broker_user_id"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(connection)
    await db.flush()

    # Sync holdings immediately
    try:
        await sync_broker_holdings(db, user_id, connection.id)
    except Exception as e:
        logger.error(f"Failed to sync Zerodha holdings on connection: {e}")
        
    await db.refresh(connection)
    
    # Return JSON response back to the frontend API caller
    return BrokerConnectionResponse.model_validate(connection)


# ── Angel One login ─────────────────────────────────────────────────────


@router.post("/connect/angelone", response_model=BrokerConnectionResponse)
@router.post("/angelone/connect", response_model=BrokerConnectionResponse)
async def connect_angelone(
    payload: BrokerConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectionResponse:
    """Connect Angel One account using client credentials + TOTP secret."""
    creds = payload.credentials
    # Support both backend and frontend keys
    client_id = creds.get("client_id") or creds.get("clientId")
    password = creds.get("password")
    totp_secret = creds.get("totp_secret") or creds.get("totp")
    
    if not client_id or not password or not totp_secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required fields: client_id/clientId, password, totp_secret/totp",
        )

    client = AngelOneClient()
    try:
        session = await client.login(
            client_id=client_id,
            password=password,
            totp_secret=totp_secret,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Angel One: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Angel One credentials: {e}",
        )

    connection = BrokerConnection(
        user_id=current_user.id,
        broker_name=BrokerName.angelone,
        encrypted_access_token=encrypt_token(session["access_token"]),
        encrypted_refresh_token=(
            encrypt_token(session["refresh_token"])
            if session.get("refresh_token")
            else None
        ),
        broker_user_id=session.get("client_id"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(connection)
    await db.flush()
    
    # Sync holdings immediately
    try:
        await sync_broker_holdings(db, current_user.id, connection.id)
    except Exception as e:
        logger.error(f"Failed to sync AngelOne holdings on connection: {e}")
        
    await db.refresh(connection)
    return BrokerConnectionResponse.model_validate(connection)


# ── Binance API key ─────────────────────────────────────────────────────


@router.post("/connect/binance", response_model=BrokerConnectionResponse)
@router.post("/binance/connect", response_model=BrokerConnectionResponse)
async def connect_binance(
    payload: BrokerConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectionResponse:
    """Connect Binance account using read-only API key + secret."""
    creds = payload.credentials
    api_key = creds.get("api_key") or creds.get("apiKey")
    api_secret = creds.get("api_secret") or creds.get("apiSecret")
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required fields: api_key/apiKey, api_secret/apiSecret",
        )

    client = BinanceClient(
        api_key=api_key,
        api_secret=api_secret,
    )
    try:
        profile = await client.get_profile()
    except Exception as e:
        logger.error(f"Failed to connect to Binance: {e}")
        await client.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Binance credentials or connection error: {e}",
        )
    finally:
        await client.close()

    connection = BrokerConnection(
        user_id=current_user.id,
        broker_name=BrokerName.binance,
        encrypted_access_token=encrypt_token(api_key),
        encrypted_refresh_token=encrypt_token(api_secret),
        broker_user_id=profile.get("broker_user_id"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(connection)
    await db.flush()
    
    # Sync holdings immediately
    try:
        await sync_broker_holdings(db, current_user.id, connection.id)
    except Exception as e:
        logger.error(f"Failed to sync Binance holdings on connection: {e}")
        
    await db.refresh(connection)
    return BrokerConnectionResponse.model_validate(connection)


# ── List / disconnect / sync ─────────────────────────────────────────────


@router.get("/connections", response_model=list[BrokerConnectionResponse])
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BrokerConnectionResponse]:
    """List all broker connections for the current user."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active.is_(True),
        ),
    )
    connections = result.scalars().all()
    return [BrokerConnectionResponse.model_validate(c) for c in connections]



@router.delete(
    "/disconnect/{connection_id}",
    status_code=status.HTTP_200_OK,
)
@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_200_OK,
)
async def disconnect_broker(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
)-> None:
    """Deactivate a broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == connection_id,
            BrokerConnection.user_id == current_user.id,
        ),
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Broker connection not found",
        )
    connection.is_active = False
    connection.updated_at = datetime.now(timezone.utc)
    await db.flush()


@router.post("/sync/{connection_id}", response_model=BrokerConnectionResponse)
@router.post("/connections/{connection_id}/sync", response_model=BrokerConnectionResponse)
async def sync_broker(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectionResponse:
    """Trigger a data sync from a specific broker connection."""
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.id == connection_id,
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active.is_(True),
        ),
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active broker connection not found",
        )
    await sync_broker_holdings(db, current_user.id, connection_id)
    await db.refresh(connection)
    return BrokerConnectionResponse.model_validate(connection)
