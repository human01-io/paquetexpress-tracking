import json
import re
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Paquetexpress Tracking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPSTREAM_URL = (
    "https://cc.paquetexpress.com.mx/ptxws/rest/api/v1/guia/historico"
)
UPSTREAM_TIMEOUT = 15

JSONP_RE = re.compile(r"^Resultado\((.+)\)$", re.DOTALL)


# ---------- Models ----------

class TrackingEvent(BaseModel):
    date: str
    time: str
    branch: str
    branch_code: str
    city: str
    status: str
    event_id: str
    timestamp: str


class TrackingSummary(BaseModel):
    tracking_number: str
    guide: str
    origin: str
    destination: str
    promise_date: str
    delivery_type: str
    current_status: str
    current_location: str
    current_branch: str
    last_update: str


class TrackingFull(TrackingSummary):
    events: list[TrackingEvent]


class DetailLevel(str, Enum):
    summary = "summary"
    full = "full"


# ---------- Helpers ----------

def strip_jsonp(text: str) -> list[dict]:
    """Extract the JSON array from a JSONP `Resultado(...)` wrapper."""
    m = JSONP_RE.match(text.strip())
    if not m:
        raise ValueError("Response is not valid JSONP")
    return json.loads(m.group(1))


def parse_event(raw: dict) -> TrackingEvent:
    return TrackingEvent(
        date=raw.get("fecha", ""),
        time=raw.get("hora", ""),
        branch=raw.get("sucursal", ""),
        branch_code=raw.get("sucursalOrigen", ""),
        city=raw.get("ciudadEvento", ""),
        status=raw.get("status", ""),
        event_id=raw.get("eventoId", ""),
        timestamp=str(raw.get("fechahora", "")),
    )


def build_summary(tracking_number: str, events: list[dict]) -> TrackingSummary:
    first = events[0]
    last = events[-1]
    return TrackingSummary(
        tracking_number=tracking_number,
        guide=first.get("guia", ""),
        origin=first.get("ciudadEvento", ""),
        destination=first.get("ciudadDestino", ""),
        promise_date=first.get("promesa", "").strip(),
        delivery_type=first.get("tipoEntrega", ""),
        current_status=last.get("status", ""),
        current_location=last.get("ciudadEvento", ""),
        current_branch=last.get("sucursal", ""),
        last_update=f"{last.get('fecha', '').strip()} {last.get('hora', '')}",
    )


# ---------- Endpoint ----------

@app.get(
    "/track/{tracking_number}",
    response_model=TrackingSummary | TrackingFull,
)
async def track(
    tracking_number: str,
    detail: DetailLevel = Query(DetailLevel.summary),
):
    url = f"{UPSTREAM_URL}/{tracking_number}/@1@2@3@4@5?source=WEBPAGE"

    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise HTTPException(502, "Upstream API timed out")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, f"Upstream returned {exc.response.status_code}")

    try:
        events_raw = strip_jsonp(resp.text)
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(502, "Failed to parse upstream response")

    if not events_raw:
        raise HTTPException(404, "No tracking data found for this number")

    # Upstream returns unrelated results for unknown numbers; verify match.
    returned_id = events_raw[0].get("rastreo", "")
    if returned_id != tracking_number:
        raise HTTPException(404, "No tracking data found for this number")

    summary = build_summary(tracking_number, events_raw)

    if detail == DetailLevel.full:
        return TrackingFull(
            **summary.model_dump(),
            events=[parse_event(e) for e in events_raw],
        )

    return summary
