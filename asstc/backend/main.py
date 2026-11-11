from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes import admin, auth, developer, launchers, seo
from backend.seed import init_and_seed_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_and_seed_db()
    yield


app = FastAPI(
    title="BLOCKHUB — Minecraft Launcher Discovery & Publishing Platform",
    description="DISCOVER. PUBLISH. PLAY. REST API & Full-Stack Platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.APP_URL, "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


static_dir = Path(__file__).resolve().parent.parent / "frontend" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth.router)
app.include_router(launchers.router)
app.include_router(developer.router)
app.include_router(admin.router)
app.include_router(seo.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "platform": settings.APP_NAME, "tagline": settings.TAGLINE}


@app.get("/")
def serve_spa():
    index_file = Path(__file__).resolve().parent.parent / "frontend" / "templates" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "BLOCKHUB API is running. Open /docs for OpenAPI specification."})


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": getattr(exc, "detail", "Resource not found on BLOCKHUB.")},
        )
    index_file = Path(__file__).resolve().parent.parent / "frontend" / "templates" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file), status_code=404)
    return JSONResponse(status_code=404, content={"detail": "404 — Page not found on BLOCKHUB."})
