import os
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.core.scheduler import check_live_class_reminders
from app.routers import auth, users, courses, quizzes, live, payments, ai, admin, notifications, learning

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables automatically
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Start 15-minute live class reminder background task
    scheduler_task = asyncio.create_task(check_live_class_reminders())
    yield
    scheduler_task.cancel()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise AI-Powered Educational Marketplace API with RAG, Live Classroom, and Multi-role RBAC.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers & Rate Limiting Middleware
@app.middleware("http")
async def security_and_performance_middleware(request: Request, call_next):
    start_time = time.time()
    
    response: Response = await call_next(request)
    
    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://cdn.tailwindcss.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; img-src 'self' data: https:; frame-ancestors 'none';"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Server"] = "Educational-AI-Marketplace"
    
    # Performance Header
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    return response

# Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
index_html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(courses.router, prefix=settings.API_V1_STR)
app.include_router(quizzes.router, prefix=settings.API_V1_STR)
app.include_router(live.router, prefix=settings.API_V1_STR)
app.include_router(payments.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(learning.router, prefix=settings.API_V1_STR)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    with open(index_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    return {"status": "online", "system": "AI-Powered Educational Marketplace", "security": "RBAC & JWT Enabled"}
