from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, listings, orders, payments, restaurants

app = FastAPI(title="FreshForward API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(payments.router)
app.include_router(restaurants.router)
app.include_router(listings.router)
app.include_router(orders.router)


@app.get("/")
def root():
    return {"status": "FreshForward API running"}