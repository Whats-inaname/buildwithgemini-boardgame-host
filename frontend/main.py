"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")

if RESOURCE.startswith("http://") or RESOURCE.startswith("https://"):
    base_url = RESOURCE.rstrip("/")
    if "/a2a/" in base_url:
        A2A_BASE = base_url
    else:
        A2A_BASE = f"{base_url}/a2a/{AGENT_DIRECTORY}"
    A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
elif "locations/" in RESOURCE and "reasoningEngines/" in RESOURCE:
    LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]
    A2A_BASE = (
        f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
        f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
    )
    A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
else:
    # Default to Cloud Run service URL format
    A2A_BASE = f"https://{RESOURCE}.run.app/a2a/{AGENT_DIRECTORY}"
    A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers(target_url: str = "") -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    try:
        from google.oauth2 import id_token
        req = google.auth.transport.requests.Request()
        aud = target_url or A2A_BASE
        # Strip path to get origin domain as target audience if full URL passed
        if aud.startswith("http://") or aud.startswith("https://"):
            parts = aud.split("/")
            aud = f"{parts[0]}//{parts[2]}"
        token = id_token.fetch_id_token(req, aud)
        headers["Authorization"] = f"Bearer {token}"
    except Exception:
        try:
            _creds.refresh(google.auth.transport.requests.Request())
            if _creds.token:
                headers["Authorization"] = f"Bearer {_creds.token}"
        except Exception:
            pass
    return headers


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        # Agent Runtime does not serve a public card URL, so point the client at
        # the passthrough base for message sends.
        card.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. A2UI data parts (tagged
    application/json+a2ui) become {"kind": "a2ui", "data": <message>} so the UI
    renders the card; each data part is one A2UI message (beginRendering or
    surfaceUpdate).
    """
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


@app.get("/api/suggestions")
async def get_personalized_suggestions(user_id: str = "web-user"):
    """Generates dynamic, personalized floating prompt suggestions based on user profiles, active gaming groups, and current context."""
    import datetime
    from google.cloud import firestore

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-f00620733056")

    suggestions = []
    try:
        db = firestore.Client(project=project_id)

        # 1. User Profile Lookup
        user_doc = db.collection("user_profiles").document(user_id).get()
        home_city = "San Francisco"
        fav_cats = ["Strategy"]
        if user_doc.exists:
            udata = user_doc.to_dict()
            home_city = udata.get("home_city", home_city)
            fav_cats = udata.get("favorite_categories", fav_cats)

        # 2. Gaming Groups Lookup
        groups = list(db.collection("gaming_groups").limit(3).stream())
        if groups:
            group_data = groups[0].to_dict()
            gname = group_data.get("group_name", "Friday Night Strategists")
            suggestions.append({"label": f"📅 Plan session for '{gname}'", "prompt": f"Start a session planner for gaming group '{gname}' with Catan, Wingspan, and Suzerain"})
            suggestions.append({"label": f"👥 View '{gname}' squad members", "prompt": f"Who is currently in the gaming squad '{gname}'?"})
        else:
            suggestions.append({"label": "👥 Create Gaming Squad", "prompt": "Create a gaming group called 'Friday Night Strategists'"})

        # 3. Time & Weather Context
        now = datetime.datetime.now(datetime.timezone.utc)
        hour = now.hour
        if "seattle" in home_city.lower() or "london" in home_city.lower():
            suggestions.append({"label": f"🌧️ Cozy game for {home_city}", "prompt": f"Recommend a cozy rainy day game for {home_city}"})
        elif 17 <= hour < 23:
            suggestions.append({"label": f"🌙 Evening Strategy for {home_city}", "prompt": f"Suggest an epic evening strategy game for 4 players in {home_city}"})
        else:
            suggestions.append({"label": f"🎲 Quick game for {home_city}", "prompt": f"Recommend a 4-player game under 60 mins suited for {home_city}"})

        # 4. Favorite Genre Suggestion
        fav_genre = fav_cats[0] if fav_cats else "Strategy"
        suggestions.append({"label": f"✨ Best {fav_genre} Games", "prompt": f"What are the top rated {fav_genre} games in our catalog?"})
        suggestions.append({"label": "🎬 Watch 3D Game Trailer", "prompt": "Generate a 3D animated trailer video for Suzerain Strategy Edition"})

    except Exception:
        suggestions = [
            {"label": "👥 Create Gaming Squad", "prompt": "Create a gaming group called 'Friday Night Strategists'"},
            {"label": "📅 Launch Game Night Planner", "prompt": "Start a session planner for 'Friday Night Strategists' this Saturday"},
            {"label": "🌧️ Environmental Game Vibe", "prompt": "Recommend a cozy rainy day game for my environment"},
            {"label": "🎲 4-Player Games", "prompt": "Recommend a game for 4 players (under 90 mins)"},
        ]

    return JSONResponse({"suggestions": suggestions})


# Serve the chat UI (keep this mount last so /chat wins).
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
