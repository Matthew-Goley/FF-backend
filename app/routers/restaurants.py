from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin, get_current_user
from app.models import Restaurant, User
from app.schemas import (
    RestaurantApplicationInput,
    RestaurantOut,
    RestaurantPublicOut,
    RestaurantRejectRequest,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.post("/apply", response_model=RestaurantOut)
def apply(
    payload: RestaurantApplicationInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    restaurant = db.query(Restaurant).filter(Restaurant.owner_user_id == current_user.id).first()

    if restaurant:
        restaurant.name = payload.name
        restaurant.contact_email = payload.contact_email
        restaurant.address = payload.address
        restaurant.description = payload.description
        restaurant.status = "pending"
        restaurant.rejection_reason = None
    else:
        restaurant = Restaurant(owner_user_id=current_user.id, status="pending", **payload.model_dump())
        db.add(restaurant)

    current_user.account_type = "restaurant"
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("/me", response_model=RestaurantOut)
def read_my_restaurant(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).filter(Restaurant.owner_user_id == current_user.id).first()
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You don't have a restaurant")
    return restaurant


@router.post("/{restaurant_id}/approve", response_model=RestaurantOut)
def approve(
    restaurant_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    restaurant.status = "approved"
    restaurant.rejection_reason = None
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.post("/{restaurant_id}/reject", response_model=RestaurantOut)
def reject(
    restaurant_id: int,
    payload: RestaurantRejectRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    restaurant.status = "rejected"
    restaurant.rejection_reason = payload.reason
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("", response_model=list[RestaurantPublicOut])
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).filter(Restaurant.status == "approved").all()


@router.get("/{restaurant_id}", response_model=RestaurantPublicOut)
def read_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None or restaurant.status != "approved":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
    return restaurant
