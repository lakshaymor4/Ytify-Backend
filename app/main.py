from fastapi import FastAPI
from app.api.routes import transfer, auth, health

app = FastAPI(title="Spotify to YouTube Music Migrator")

app.include_router(transfer.router, prefix="/transfer", tags=["Transfer"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(health.router, prefix="/health", tags=["Health"])
