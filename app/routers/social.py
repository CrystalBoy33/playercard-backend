from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Endorsement, KeystoneRun, Player
from app.schemas import EndorsementCreate, EndorsementOut, KeystoneRunCreate

router = APIRouter(tags=["social"])


# ===== Endorsements =====

endorse_router = APIRouter(prefix="/endorsements")

@endorse_router.post("/", response_model=EndorsementOut, status_code=201)
def add_endorsement(data: EndorsementCreate, db: Session = Depends(get_db)):
    existing = db.query(Endorsement).filter(
        Endorsement.player_key == data.player_key,
        Endorsement.author == data.author,
        Endorsement.badge == data.badge,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already endorsed with this badge.")

    end = Endorsement(**data.model_dump())
    db.add(end)
    db.commit()
    db.refresh(end)
    return EndorsementOut.model_validate(end)


# ===== Keystone runs =====

keystone_router = APIRouter(prefix="/keystones")

@keystone_router.post("/", status_code=201)
def record_keystone_run(data: KeystoneRunCreate, db: Session = Depends(get_db)):
    run = KeystoneRun(**data.model_dump())
    db.add(run)
    db.commit()
    return {"recorded": True}


@keystone_router.get("/{player_key}", response_model=list[dict])
def get_keystone_history(player_key: str, db: Session = Depends(get_db)):
    runs = db.query(KeystoneRun).filter(
        KeystoneRun.player_key == player_key
    ).order_by(KeystoneRun.ran_at.desc()).limit(50).all()

    return [
        {
            "partner":  r.partner,
            "map_id":   r.map_id,
            "level":    r.level,
            "ran_at":   r.ran_at.isoformat(),
        }
        for r in runs
    ]


@keystone_router.get("/{player_key}/partners")
def get_partners(player_key: str, db: Session = Depends(get_db)):
    """Returns list of player_keys this player has done keys with."""
    runs = db.query(KeystoneRun.partner).filter(
        KeystoneRun.player_key == player_key
    ).distinct().all()
    return [r.partner for r in runs]
