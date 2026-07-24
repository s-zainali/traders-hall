from fastapi import APIRouter

from app.api.v1 import auth, config, games, actions, feed

api_router = APIRouter()


# api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(config.router, prefix="/config", tags=["Reference"])
api_router.include_router(games.router, prefix="/games", tags=["Games"])
api_router.include_router(actions.router, prefix="/games", tags=["Actions"])
api_router.include_router(feed.router, prefix="/games", tags=["Feed"])