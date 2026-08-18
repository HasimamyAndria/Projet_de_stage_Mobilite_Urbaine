from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.routers import map
from app.routers import zones
from app.routers import od
from app.routers import keypoints
from app.routers import emploi_habitat
from app.routers import cities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("mobilite.api")

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PROD = APP_ENV in {"production", "prod"}

# Swagger / ReDoc désactivés en production (démo publique / réseau non contrôlé)
_docs = None if IS_PROD else "/docs"
_redoc = None if IS_PROD else "/redoc"
_openapi = None if IS_PROD else "/openapi.json"

app = FastAPI(
    title="Urban Mobility API",
    docs_url=_docs,
    redoc_url=_redoc,
    openapi_url=_openapi,
)

# CORS configurable (prod / docker / vite) — jamais "*"
_default_origins = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://localhost:8080,"
    "http://127.0.0.1:8080"
)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if o.strip() and o.strip() != "*"
]
logger.info("APP_ENV=%s CORS_ORIGINS=%s", APP_ENV, CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)

app.include_router(map.router)
app.include_router(zones.router)
app.include_router(od.router)
app.include_router(keypoints.router)
app.include_router(emploi_habitat.router)
app.include_router(cities.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": APP_ENV}
