from fastapi import APIRouter

from app.api.v1 import (
    actions,
    auth,
    config,
    feed,
    food,
    games,
    loans,
    offers,
    residence,
)

api_router = APIRouter()


api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(config.router, prefix="/config", tags=["Reference"])
api_router.include_router(games.router, prefix="/games", tags=["Games"])
api_router.include_router(actions.router, prefix="/games", tags=["Actions"])
api_router.include_router(loans.router, prefix="/games", tags=["Credit"])
api_router.include_router(food.router, prefix="/games", tags=["Upkeep"])
api_router.include_router(residence.router, prefix="/games", tags=["Housing"])
api_router.include_router(feed.router, prefix="/games", tags=["Feed"])
api_router.include_router(offers.router, prefix="/games", tags=["Offers"])