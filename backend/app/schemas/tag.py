import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str | None = Field(None, max_length=20)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Convert empty string to None"""
        if v == "":
            return None
        return v


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, max_length=20)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Convert empty string to None"""
        if v == "":
            return None
        return v


class TagResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    color: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int
