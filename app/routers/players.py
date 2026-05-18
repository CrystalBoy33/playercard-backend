from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.database import get_db
from app.models.models import Player, Review, Endorsement, KeystoneRun
from app.schemas import (
    PlayerCreate, PlayerOut, PlayerProfile,
    ReviewOut, EndorsementCount, RoleRating
)

router = APIRouter(prefix="/players", tags=["players"])


def upsert_player(db: Session, data: PlayerCreate) -> Player:
    player = db.get(Player, data.player_key)
    if not player:
        player = Player(**data.model_dump())
        db.add(player)
    else:
        for k, v in data.model_dump(exclude_unset=True).items():
            if v is not None:
                setattr(player, k, v)
    db.commit()
    db.refresh(player)
    return player


def recalculate_rating(db: Session, player_key: str):
    result = db.query(
        func.avg(Review.rating).label("avg"),
        func.count(Review.id).label("cnt")
    ).filter(
        Review.player_key == player_key,
        Review.report_count < 3
    ).first()

    player = db.get(Player, player_key)
    if player:
        player.avg_rating   = round(float(result.avg or 0), 2)
        player.review_count = result.cnt or 0
        db.commit()


@router.get("/{player_key}", response_model=PlayerProfile)
def get_player(player_key: str, db: Session = Depends(get_db)):
    player = db.get(Player, player_key)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    reviews = db.query(Review).filter(
        Review.player_key == player_key
    ).order_by(Review.created_at.desc()).all()

    # Endorsement counts
    end_rows = db.query(
        Endorsement.badge,
        func.count(Endorsement.id).label("cnt")
    ).filter(
        Endorsement.player_key == player_key
    ).group_by(Endorsement.badge).all()

    endorsements = [EndorsementCount(badge=r.badge, count=r.cnt) for r in end_rows]

    # Per-role averages
    role_rows = db.query(
        Review.role,
        func.avg(Review.rating).label("avg"),
        func.count(Review.id).label("cnt")
    ).filter(
        Review.player_key == player_key,
        Review.report_count < 3
    ).group_by(Review.role).all()

    role_ratings = [
        RoleRating(role=r.role, avg_rating=round(float(r.avg), 2), review_count=r.cnt)
        for r in role_rows if r.role != "UNKNOWN"
    ]

    # Keystone run count with this player
    keystone_count = db.query(KeystoneRun).filter(
        KeystoneRun.player_key == player_key
    ).count()

    return PlayerProfile(
        player         = PlayerOut.model_validate(player),
        reviews        = [ReviewOut.model_validate(r) for r in reviews],
        endorsements   = endorsements,
        role_ratings   = role_ratings,
        keystone_count = keystone_count,
    )


@router.post("/upsert", response_model=PlayerOut, status_code=200)
def upsert(data: PlayerCreate, db: Session = Depends(get_db)):
    return upsert_player(db, data)


@router.get("/search/{name}", response_model=list[PlayerOut])
def search_players(name: str, db: Session = Depends(get_db)):
    results = db.query(Player).filter(
        Player.name.ilike(f"%{name}%")
    ).limit(20).all()
    return results
