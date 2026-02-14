# Paquetexpress Tracking API

FastAPI wrapper around the Paquetexpress public tracking endpoint. Strips the JSONP response and returns clean, typed JSON.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API docs at `http://localhost:8000/docs`

## Endpoints

### `GET /track/{tracking_number}`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `tracking_number` | path | — | Paquetexpress tracking number |
| `detail` | query | `summary` | `summary` or `full` |

**Summary response** (default):

```json
{
  "tracking_number": "631234827297",
  "guide": "CVJ01WE247372",
  "origin": "Civac, Morelos, Mexico",
  "destination": "Villahermosa, Tabasco, Mexico",
  "promise_date": "13 de Febrero del 2026",
  "delivery_type": "ENT_EAD",
  "current_status": "Mercancía En Tránsito",
  "current_location": "Cuautitlan Izcalli, Estado De Mexico, Mexico",
  "current_branch": "Mexico",
  "last_update": "12 De Febrero Del 2026 13:19"
}
```

**Full response** (`?detail=full`): same fields plus an `events` array with full tracking history (oldest to newest).

## Deploy to Railway

1. Create a new Railway project from the GitHub repo
2. Railway auto-detects the `Procfile` and sets the `PORT` env var
3. No additional configuration needed
