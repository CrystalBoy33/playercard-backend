from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import create_tables
from app.routers import players, reviews
from app.routers.social import endorse_router, keystone_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="PlayerCard API",
    description="Global review system for World of Warcraft players",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "name":    "PlayerCard API",
        "version": "1.0.0",
        "docs":    "/docs",
    }


# Rate-limited sync endpoint (called by companion app)
@app.post("/sync")
@limiter.limit("60/minute")
async def sync(request: Request):
    """Bulk sync endpoint for companion app — accepts batched reviews."""
    body = await request.json()
    return {"received": len(body.get("reviews", []))}


app.include_router(players.router)
app.include_router(reviews.router)
app.include_router(endorse_router)
app.include_router(keystone_router)
