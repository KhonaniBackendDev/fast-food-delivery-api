import logging
import time
from fastapi import FastAPI , Request
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from .database import engine
from . import models
from .routers import (
    auth,
    users,
    auth,
    profile,
    restaurants,
    foods,
    orders,
    ratings,
    addresses,
    payments,
    tracking,
    verification,
)

# ─── LOGGING SETUP ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

security=HTTPBearer()

app = FastAPI(
    title="Fast Food Delivery API",
    description="A food delivery API built with FastAPI",
    root_path_in_servers=False
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Fast Food Delivery API",
        description="A production-ready food delivery REST API",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ─── CORS MIDDLEWARE ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"→ {request.method} {request.url} - IP: {request.client.host}")
    response : Response = await call_next(request)
    process_time = round(time.time() - start_time, 3)
    logger.info(
        f"← {request.method} {request.url} "
        f"- Status: {response.status_code} "
        f"- Time: {process_time}s"
    )
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled error on {request.method} {request.url}: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ─── ROUTERS ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(restaurants.router)
app.include_router(foods.router)
app.include_router(orders.router)
app.include_router(ratings.router)
app.include_router(addresses.router)
app.include_router(payments.router)
app.include_router(tracking.router)
app.include_router(verification.router)


@app.get("/")
def root():
    return {"message": "Welcome to the UberEats Clone API"}
