from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ===== Player =====

class PlayerCreate(BaseModel):
    player_key:   str = Field(..., max_length=120)
    name:         str = Field(..., max_length=60)
    realm:        str = Field(..., max_length=60)
    player_class: Optional[str] = None
    spec:         Optional[str] = None
    guild:        Optional[str] = None
    item_level:   Optional[int] = None


class PlayerOut(BaseModel):
    player_key:   str
    name:         str
    realm:        str
    player_class: Optional[str]
    spec:         Optional[str]
    guild:        Optional[str]
    item_level:   Optional[int]
    avg_rating:   float
    review_count: int
    updated_at:   datetime

    model_config = {"from_attributes": True}


# ===== Review =====

VALID_ROLES = {"TANK", "HEALER", "DPS", "UNKNOWN"}

class ReviewCreate(BaseModel):
    player_key: str  = Field(..., max_length=120)
    author:     str  = Field(..., max_length=60)
    rating:     int  = Field(..., ge=1, le=5)
    role:       str  = Field(default="UNKNOWN")
    text:       str  = Field(..., min_length=1, max_length=200)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        v = v.upper()
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of {VALID_ROLES}")
        return v


class ReviewEdit(BaseModel):
    rating: int  = Field(..., ge=1, le=5)
    role:   str  = Field(default="UNKNOWN")
    text:   str  = Field(..., min_length=1, max_length=200)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        v = v.upper()
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of {VALID_ROLES}")
        return v


class ReviewReply(BaseModel):
    text: str = Field(..., min_length=1, max_length=100)


class ReviewOut(BaseModel):
    id:          int
    player_key:  str
    author:      str
    rating:      int
    role:        str
    text:        str
    reply:       Optional[str]
    edited:      bool
    report_count: int
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


# ===== Endorsement =====

VALID_BADGES = {
    "Carries the group",
    "Great callouts",
    "Always prepared",
    "Friendly",
    "Reliable",
    "Fast learner",
}

class EndorsementCreate(BaseModel):
    player_key: str = Field(..., max_length=120)
    author:     str = Field(..., max_length=60)
    badge:      str

    @field_validator("badge")
    @classmethod
    def validate_badge(cls, v):
        if v not in VALID_BADGES:
            raise ValueError(f"Unknown badge: {v}")
        return v


class EndorsementOut(BaseModel):
    id:         int
    player_key: str
    author:     str
    badge:      str
    created_at: datetime

    model_config = {"from_attributes": True}


# ===== Keystone =====

class KeystoneRunCreate(BaseModel):
    player_key: str = Field(..., max_length=120)
    partner:    str = Field(..., max_length=120)
    map_id:     int = Field(default=0)
    level:      int = Field(default=0, ge=0)


# ===== Aggregated profile =====

class RoleRating(BaseModel):
    role:         str
    avg_rating:   float
    review_count: int


class EndorsementCount(BaseModel):
    badge:  str
    count:  int


class PlayerProfile(BaseModel):
    player:       PlayerOut
    reviews:      list[ReviewOut]
    endorsements: list[EndorsementCount]
    role_ratings: list[RoleRating]
    keystone_count: int
