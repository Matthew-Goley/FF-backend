from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_restaurant
from app.models import Listing, Restaurant
from app.schemas import ListingInput, ListingOut

router = APIRouter(tags=["listings"])


@router.get("/listings", response_model=list[ListingOut])
def list_listings(db: Session = Depends(get_db)):
    return (
        db.query(Listing)
        .join(Restaurant)
        .filter(Restaurant.status == "approved")
        .all()
    )


@router.get("/listings/{listing_id}", response_model=ListingOut)
def read_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.restaurant.status != "approved":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


@router.get("/restaurants/me/listings", response_model=list[ListingOut])
def read_my_listings(
    restaurant: Restaurant = Depends(get_current_restaurant), db: Session = Depends(get_db)
):
    return db.query(Listing).filter(Listing.restaurant_id == restaurant.id).all()


@router.post("/restaurants/me/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingInput,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db),
):
    listing = Listing(restaurant_id=restaurant.id, **payload.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def _get_owned_listing(listing_id: int, restaurant: Restaurant, db: Session) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.restaurant_id != restaurant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")
    return listing


@router.put("/restaurants/me/listings/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: int,
    payload: ListingInput,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db),
):
    listing = _get_owned_listing(listing_id, restaurant, db)
    for field, value in payload.model_dump().items():
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/restaurants/me/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db),
):
    listing = _get_owned_listing(listing_id, restaurant, db)
    if listing.orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can't delete a listing that has orders against it",
        )
    db.delete(listing)
    db.commit()
