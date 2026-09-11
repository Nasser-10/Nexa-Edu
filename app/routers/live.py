import json, uuid
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.schema import LiveClass, LiveClassStatus, User, UserRole, Course
from app.schemas.validation import LiveClassCreate, LiveClassOut

router = APIRouter(prefix="/live", tags=["Live Classroom"])

# WebSocket Connection Manager for real-time live classroom rooms
class ConnectionManager:
    def __init__(self):
        # room_code -> list of WebSocket connections
        self.active_rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.active_rooms:
            self.active_rooms[room_code] = []
        self.active_rooms[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.active_rooms:
            if websocket in self.active_rooms[room_code]:
                self.active_rooms[room_code].remove(websocket)
            if not self.active_rooms[room_code]:
                del self.active_rooms[room_code]

    async def broadcast(self, room_code: str, message: dict, sender: WebSocket = None):
        if room_code in self.active_rooms:
            for connection in self.active_rooms[room_code]:
                if connection != sender:
                    await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@router.post("/schedule", response_model=LiveClassOut, status_code=status.HTTP_201_CREATED)
async def schedule_live_class(
    live_in: LiveClassCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    room_code = f"room-{uuid.uuid4().hex[:8]}"
    live_class = LiveClass(
        course_id=live_in.course_id,
        teacher_id=current_user.id,
        title=live_in.title,
        description=live_in.description,
        scheduled_at=live_in.scheduled_at,
        status=LiveClassStatus.SCHEDULED,
        room_code=room_code
    )
    db.add(live_class)
    await db.commit()
    await db.refresh(live_class)
    return live_class

@router.get("/course/{course_id}")
async def get_course_live_classes(course_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(LiveClass).where(LiveClass.course_id == course_id).order_by(LiveClass.scheduled_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.websocket("/ws/{room_code}")
async def live_classroom_ws(websocket: WebSocket, room_code: str):
    await manager.connect(room_code, websocket)
    try:
        # Send initial welcome event
        await websocket.send_text(json.dumps({
            "type": "SYSTEM_EVENT",
            "message": f"Connected to Live Classroom [{room_code}]",
            "room_code": room_code
        }))
        
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            
            # Types: CHAT_MESSAGE, WHITEBOARD_DRAW, RAISE_HAND, MEDIA_STATUS, WEBRTC_OFFER, WEBRTC_ANSWER, ICE_CANDIDATE
            # WebSocket only relays signaling/events; actual audio/video media should use WebRTC/SFU.
            await manager.broadcast(room_code, data, sender=None)
            
    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
        await manager.broadcast(room_code, {
            "type": "USER_LEFT",
            "message": "A participant left the classroom."
        })
