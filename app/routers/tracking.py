from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session
from sqlalchemy import select
from .. import models
from ..database import get_db, SessionLocal
from typing import Dict, Any
import json
from ..utils.oauth2 import verify_access_token
from fastapi import HTTPException, status

router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ─── CONNECTION MANAGER ───────────────────────────────────
# This manages all active WebSocket connections


class ConnectionManager:
    def __init__(self):
        # Dictionary of order_id → list of connected clients
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, order_id: str):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)

    def disconnect(self, websocket: WebSocket, order_id: str):
        if order_id in self.active_connections:
            self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]

    async def send_location_update(self, order_id: str, data: dict):
        if order_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[order_id]:
                try:
                    await connection.send_json(data)
                except Exception:
                    disconnected.append(connection)
            # Clean up disconnected clients
            for connection in disconnected:
                self.active_connections[order_id].remove(connection)


manager = ConnectionManager()


# ─── CLIENT TRACKING WEBSOCKET ────────────────────────────
# Client connects to this to track their order in real time


@router.websocket("/track/{order_public_id}/{token}")
async def track_order(
    websocket: WebSocket,
    order_public_id: str,
    token: str,
    
):
    db = SessionLocal()
    try:
        # 1. Verify token manually since WebSockets don't support headers
        
        

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

        token_data= verify_access_token(token, credentials_exception)

        user = db.execute(
            select(models.User).where(models.User.public_id == token_data.id)
        ).scalar_one_or_none()

        if not user:
            await websocket.close(code=4001)
            return

        # 2. Verify order belongs to this user
        order = db.execute(
            select(models.Order).where(
                models.Order.public_id == order_public_id, models.Order.user_id == user.id
            )
        ).scalar_one_or_none()

        if not order:
            await websocket.close(code=4004)
            return

        # 3. Connect the client
        await manager.connect(websocket, order_public_id)
        
          # 4. Send initial order status
        await websocket.send_json(
            {
                "type": "order_status",
                "order_id": order_public_id,
                "status": order.status.value,
                "message": "Connected to order tracking",
            }
        )

        # 5. Keep connection alive and listen for messages
        while True:
            data = await websocket.receive_text()
            # Client can send a ping to keep connection alive
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, order_public_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        db.close()  
        
    


# ─── DRIVER LOCATION UPDATE ───────────────────────────────
# Driver sends their location → we broadcast to the client


@router.websocket("/driver/{order_public_id}/{token}")
async def driver_location(
    websocket: WebSocket,
    order_public_id: str,
    token: str,
    
):
    db = SessionLocal()  
    try:
        # 1. Verify token
        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
        
        await websocket.accept()

        try:
            token_data = verify_access_token(token, credentials_exception)
        except Exception:
            await websocket.close(code=4001)
            return

        user = db.execute(
            select(models.User).where(models.User.public_id == token_data.id)
        ).scalar_one_or_none()

        if not user:
            await websocket.close(code=4001)
            return


    
        while True:
            # 3. Receive location from driver
            data = await websocket.receive_text()
            location_data:Dict[str, Any] = json.loads(data) 

            # 4. Validate location data
            if "latitude" not in location_data or "longitude" not in location_data:
                await websocket.send_json(
                    {
                        "error": "Invalid location data. Must include latitude and longitude"
                    }
                )
                continue

            # 5. Broadcast location to all clients tracking this order
            await manager.send_location_update(
                order_public_id,
                {
                    "type": "location_update",
                    "order_id": order_public_id,
                    "latitude": location_data["latitude"],
                    "longitude": location_data["longitude"],
                    "timestamp": location_data.get("timestamp"),
                },
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Driver WebSocket error: {e}")
    finally:
        db.close()


# ─── HTTP ENDPOINT TO UPDATE ORDER STATUS ─────────────────
# When owner updates order status, we notify the client via WebSocket


@router.post("/notify/{order_public_id}")
async def notify_order_status(order_public_id: str, db: Session = Depends(get_db)):
    order = db.execute(
        select(models.Order).where(models.Order.public_id == order_public_id)
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Send status update to all connected clients
    await manager.send_location_update(
        order_public_id,
        {
            "type": "order_status",
            "order_id": order_public_id,
            "status": order.status.value,
            "message": f"Your order is now {order.status.value}",
        },
    )

    return {"message": "Notification sent"}
