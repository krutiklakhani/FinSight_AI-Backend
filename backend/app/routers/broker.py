"""
Broker router – connect / disconnect / sync broker accounts.
Supports multiple routing patterns to align with frontend API requests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import cache_set
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
    payload: BrokerConnectRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectionResponse | dict:
    """Connect Zerodha account using direct credentials or return OAuth login URL."""
    creds = payload.credentials if payload else {}
    api_key = creds.get("api_key") or creds.get("apiKey")
    access_token = creds.get("access_token") or creds.get("accessToken")
    
    if api_key and access_token:
        # Bypass OAuth, connect directly
        client = ZerodhaClient(access_token=access_token, api_key=api_key)
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
    await cache_set(f"zerodha_state:{state}", str(current_user.id), ttl=600)
    client = ZerodhaClient()
    login_url = client.get_login_url()
    return {"login_url": login_url, "state": state}


@router.get("/callback/zerodha")
async def callback_zerodha(
    request_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectionResponse:
    """Handle the OAuth callback from Zerodha, store encrypted token and sync."""
    client = ZerodhaClient()
    access_token = await client.handle_callback(request_token)
    profile = await client.get_profile()

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
    session = await client.login(
        client_id=client_id,
        password=password,
        totp_secret=totp_secret,
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
