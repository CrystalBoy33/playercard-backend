# PlayerCard Backend

Global review system for World of Warcraft players.

## Architecture

```
WoW Addon (Lua)
    ↕ SavedVariables file
Companion App (Python)
    ↕ HTTP REST
FastAPI (Python)
    ↕ SQLAlchemy ORM
PostgreSQL
```

---

## Quick start (local dev with SQLite)

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Copy env file
cp .env.example .env

# 3. Start the API (uses SQLite automatically in dev)
uvicorn app.main:app --reload

# 4. Visit http://localhost:8000/docs for the interactive API explorer

# 5. In a separate terminal, start the companion app
python companion.py
```

---

## Production setup (PostgreSQL on Railway or Render)

### 1. Create a PostgreSQL database
On Railway: New Project → Database → PostgreSQL → copy the DATABASE_URL

### 2. Set environment variables
```
DATABASE_URL=postgresql://user:pass@host:5432/playercard
SECRET_KEY=your-random-secret-key
ENVIRONMENT=production
```

### 3. Deploy the API
```bash
# Railway (recommended)
railway up

# Or Render: connect your GitHub repo, set env vars, deploy
```

### 4. Run the companion app locally
```bash
python companion.py --api-url https://your-api.railway.app
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/players/{player_key}` | Full profile with reviews, endorsements, role ratings |
| POST | `/players/upsert` | Create or update a player |
| GET | `/players/search/{name}` | Search players by name |
| POST | `/reviews/` | Submit a new review |
| PUT | `/reviews/{player_key}/{author}` | Edit your review |
| DELETE | `/reviews/{player_key}/{author}` | Delete your review |
| POST | `/reviews/{player_key}/{author}/reply` | Reply to a review |
| POST | `/reviews/{player_key}/{author}/report` | Report a review |
| POST | `/endorsements/` | Add an endorsement |
| POST | `/keystones/` | Record a keystone run |
| GET | `/keystones/{player_key}` | Get keystone history |
| GET | `/keystones/{player_key}/partners` | Get keystone partners |

Full interactive docs at `/docs` when running.

---

## Companion App

The companion app bridges WoW and the API — WoW addons can't make HTTP requests directly.

```bash
python companion.py
# Options:
#   --wow-path  "C:\Program Files (x86)\World of Warcraft\_retail_"
#   --api-url   "https://api.playercard.gg"
```

It polls the `PlayerCard.lua` SavedVariables file every 5 seconds.
When a change is detected, it parses the Lua file and pushes new reviews,
endorsements, and keystone runs to the API.

---

## Monetization options

Once the user base grows:

1. **playercard.gg website** — public profiles, leaderboards, stats pages.
   Monetize with display ads or a "Pro" subscription for advanced analytics.

2. **API tiers** — free tier (100 req/day), paid tier for addon developers
   who want to integrate PlayerCard data in their own addons.

3. **Verified badge** — optional paid cosmetic for players who want to
   claim their profile and add social links.

---

## Project structure

```
playercard-backend/
├── app/
│   ├── main.py          ← FastAPI app, middleware, routes
│   ├── database.py      ← SQLAlchemy engine + session
│   ├── schemas.py       ← Pydantic request/response models
│   ├── models/
│   │   └── models.py    ← SQLAlchemy ORM models
│   └── routers/
│       ├── players.py   ← GET/POST /players
│       ├── reviews.py   ← CRUD /reviews
│       └── social.py    ← /endorsements + /keystones
├── companion.py         ← Companion app (runs alongside WoW)
├── requirements.txt
└── .env.example
```
