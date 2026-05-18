from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Review, Player
from app.schemas import ReviewCreate, ReviewEdit, ReviewReply, ReviewOut
from app.routers.players import upsert_player, recalculate_rating
from app.schemas import PlayerCreate

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_or_404(db: Session, player_key: str, author: str) -> Review:
    review = db.query(Review).filter(
        Review.player_key == player_key,
        Review.author == author
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/", response_model=ReviewOut, status_code=201)
def create_review(data: ReviewCreate, db: Session = Depends(get_db)):
    # Ensure player exists
    if not db.get(Player, data.player_key):
        name, realm = (data.player_key.split("-", 1) + ["Unknown"])[:2]
        upsert_player(db, PlayerCreate(player_key=data.player_key, name=name, realm=realm))

    # Check duplicate
    existing = db.query(Review).filter(
        Review.player_key == data.player_key,
        Review.author == data.author
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already reviewed this player.")

    review = Review(**data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    recalculate_rating(db, data.player_key)
    return ReviewOut.model_validate(review)


@router.post("/{player_key}/{author}/edit", response_model=ReviewOut)
def edit_review(
    player_key: str, author: str,
    data: ReviewEdit, db: Session = Depends(get_db)
):
    review = get_or_404(db, player_key, author)
    review.rating = data.rating
    review.role   = data.role
    review.text   = data.text
    review.edited = True
    db.commit()
    db.refresh(review)
    recalculate_rating(db, player_key)
    return ReviewOut.model_validate(review)


@router.delete("/{player_key}/{author}", status_code=204)
def delete_review(player_key: str, author: str, db: Session = Depends(get_db)):
    review = get_or_404(db, player_key, author)
    db.delete(review)
    db.commit()
    recalculate_rating(db, player_key)


@router.post("/{player_key}/{author}/reply", response_model=ReviewOut)
def reply_to_review(
    player_key: str, author: str,
    data: ReviewReply, db: Session = Depends(get_db)
):
    review = get_or_404(db, player_key, author)
    review.reply = data.text
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)


@router.post("/{player_key}/{author}/report", status_code=200)
def report_review(
    player_key: str, author: str,
    reporter: str,
    db: Session = Depends(get_db)
):
    review = get_or_404(db, player_key, author)
    review.report_count += 1
    db.commit()
    # Recalculate in case review is now filtered
    if review.report_count >= 3:
        recalculate_rating(db, player_key)
    return {"reported": True, "report_count": review.report_count}
