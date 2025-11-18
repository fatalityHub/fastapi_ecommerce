from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, DateTime, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    comment: Mapped[str] = mapped_column(Text)
    comment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now,
                                                   nullable=False)
    grade: Mapped[int] = mapped_column(Integer,
                                       CheckConstraint("grade >=1 AND grade <= 5"),
                                       nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="reviews", lazy='joined')
    product = relationship("Product", back_populates="reviews", lazy='joined')


if __name__ == "__main__":
    Base.metadata.clear()

    from sqlalchemy.schema import CreateTable
    from app.models.categories import Category
    from app.models.products import Product

    print(CreateTable(Category.__table__))
    print(CreateTable(Product.__table__))
    print(CreateTable(Review.__table__))
