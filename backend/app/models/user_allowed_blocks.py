"""
User allowed blocks model - DEPRECATED.

This model is no longer used for restrictions. The table remains in the database
for backward compatibility but is not actively used. The platform is now fully self-paced.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserAllowedBlock(Base):
    """User's allowed blocks for practice (enforces progression fairness)."""

    __tablename__ = "user_allowed_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    year_id = Column(
        Integer,
        ForeignKey("years.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_id = Column(
        Integer,
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="allowed_blocks")
    year = relationship("Year", backref="user_allowed_blocks")
    block = relationship("Block", backref="user_allowed_blocks")

    __table_args__ = (
        UniqueConstraint("user_id", "year_id", "block_id", name="uq_user_allowed_block"),
    )
