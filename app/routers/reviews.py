from itertools import product

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db
from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.schemas import ReviewSchema, ReviewCreate
from app.models.users import User as UserModel
from app.auth import get_current_buyer, get_current_admin

from sqlalchemy.sql import func


async def update_product_rating(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    product.rating = avg_rating
    await db.commit()


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)
# создаём маршрутизатор для товаров
other_router = APIRouter(tags=["other"])


@router.get("/", response_model=list[ReviewSchema])
async def get_reviews(db: AsyncSession = Depends(get_async_db)):
    """Получить все отзывы"""
    result = await db.scalars(select(ReviewModel).where(ReviewModel.is_active == True))
    return result.all()


@other_router.get("/products/{product_id}/reviews/", response_model=list[ReviewSchema])
async def get_product_reviews(product_id: int,
                              db: AsyncSession = Depends(get_async_db)):
    """Получить все отзывы для товара"""
    stmt = await db.scalars(select(ProductModel).where(ProductModel.id == product_id,
                                                       ProductModel.is_active == True))
    product = stmt.first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found")

    reviews = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product.id,
                                  ReviewModel.is_active == True))

    return reviews.all()


@router.post("/", response_model=ReviewSchema)
async def create_review(review: ReviewCreate, db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_buyer)):
    """Создать отзыв, только для пользователей с ролью buyer"""
    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.id == review.product_id,
                                   ProductModel.is_active == True))
    product = product_result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or inactive")

    users_check = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product.id,
                                  ReviewModel.user_id == current_user.id,
                                  ReviewModel.is_active == True))
    user = users_check.first()
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Review already exists")

    new_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    await update_product_rating(db, product.id)

    return new_review


@router.delete("/{review_id}", response_model=ReviewSchema)
async def delete_review(review_id: int, db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_admin)):
    result = await db.scalars(
        select(ReviewModel).where(ReviewModel.id == review_id,
                                  ReviewModel.is_active == True)
    )
    review = result.first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Review not found")

    await db.execute(
        update(ReviewModel).where(ReviewModel.id == review_id).values(is_active=False)
    )
    await db.commit()
    await db.refresh(review)
    await update_product_rating(db, review.product_id)

    return {"message": "Review deleted"}
