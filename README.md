# 🎲 Board Game Night Host AI Agent

An intelligent, multi-tool AI board game night host and rule assistant built using Google's Agent Development Kit (ADK) and deployed to Google Cloud Agent Platform.

![Board Game Night Host Demo](./demo.gif)

---

## 🌟 What the Agent Does

The **Board Game Night Host** helps player groups organize game nights, recommend board games tailored to player counts and time constraints, summarize complex game rules, log game sessions, generate custom box art, and search for nearby board game venues.

---

## 🚀 Wired Google Cloud Services & Tools

Based on the actual implementation in `app/` and `agents-cli-manifest.yaml`, the agent includes the following active tools and services:

### 🛠️ Active Tools & Capabilities
* **Firestore Catalog & Session Store (`google.cloud.firestore`)**:
  * `search_board_games`: Queries the Firestore `board_games` database filtering by player count, duration, and category.
  * `get_board_game_rules`: Fetches rules, setup steps, and complexity details for cataloged board games.
  * `add_board_game_to_catalog`: Allows adding new board games to the Firestore database.
  * `log_game_session`: Records played game session results and scores into Firestore.
* **Vertex AI Memory Bank**:
  * `PreloadMemoryTool` & durable memory callback: Persists player group preferences (e.g. favorite games, player counts) across chat sessions.
* **Vertex AI Gemini Image Generation (`gemini-3.1-flash-lite-image`)**:
  * `generate_board_game_art`: Generates custom box art, card illustrations, or game pieces.
* **Vertex AI Gemini Omni Video Generation (`gemini-omni-flash-preview`)**:
  * `generate_board_game_trailer_video`: Generates short 3D animated trailer videos for board games.
* **Google Cloud Storage (`google.cloud.storage`)**:
  * Stores generated images and videos in a public bucket (`board-game-host-media-*`) and returns public HTTPS URLs.
* **Agent Engine Code Sandbox**:
  * `AgentEngineSandboxCodeExecutor`: Runs Python code in a secure sandbox to calculate game scores and math.
* **Google Maps Places & Geocoding APIs**:
  * `geocode_address` & `find_nearby_places`: Finds nearby board game cafes and gaming venues using Google Maps Places API.
* **A2UI Rich Card System & FastAPI Proxy**:
  * Renders structured display cards (A2UI) in the frontend for game recommendations and catalog views.

---

## 📋 Status of Planned Features

* **Vertex AI RAG Engine Document Search**: *Planned, not yet implemented.*

---

## 💻 Local Setup & Running Instructions

### Prerequisites
* Python 3.11+
* `uv` package manager (`pip install uv`)
* Google Cloud authentication configured (`gcloud auth application-default login`)

### Running the ADK Development Server
To launch the agent locally in the ADK web interface:

```bash
# Install dependencies
uv sync

# Start the ADK web server
uv run adk web app
```

### Running the Custom Chat Frontend
To launch the standalone FastAPI proxy chat interface locally:

```bash
cd frontend

# Set environment variables
export AGENT_ENGINE_RESOURCE_NAME="<your-agent-endpoint>"
export AGENT_DIRECTORY="app"

# Start the FastAPI web proxy
uv run python main.py
```
