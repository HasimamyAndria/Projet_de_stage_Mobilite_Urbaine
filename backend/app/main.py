from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import map
from app.routers import zones

print("Router chargé")
app = FastAPI(
    title="Urban Mobility API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(map.router)
app.include_router(zones.router)