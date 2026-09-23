# 🎲 Board Game Night Host AI Agent

An intelligent, multi-tool AI board game night host and rule assistant built using Google's Agent Development Kit (ADK) and deployed to Google Cloud Agent Platform.

![Board Game Night Host Demo](./demo.gif)

🎬 **[Watch full HD Walkthrough Video (MP4)](./docs/demo_walkthrough.mp4)**

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
  * `add_board_game_to_catalog`: Allows adding new board games with custom rules to the Firestore database.
  * `log_game_session`: Records played game session results and scores into Firestore.
* **Gaming Squads, Session Planners & ELO Leaderboards (`app.group_tools` & `app.leaderboard_tools`)**:
  * `create_gaming_group` & `join_gaming_group`: Organizes named player squads in Firestore.
  * `create_session_planner`, `vote_for_planner_game`, & `synthesize_group_planner_recommendation`: Launches game night voting sessions for player squads and synthesizes winning game decisions.
  * `record_game_match_result` & `get_squad_leaderboard`: Tracks match outcomes, computes ELO rating gains/losses ($K=32$), tracks win streaks, and crowns squad champions.
* **Environmental & Situational Context Engine (`get_situational_environment_context`)**:
  * Dynamically evaluates real-time weather, time of day, location, event type (e.g. cozy rainy afternoon, late night fast-paced session), and available time constraints to curate optimal game recommendations.
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

## 📚 RAG Engine Document Search & Game Doc Generation

* **Automatic RAG Game Doc Generation**: Every game added via `add_board_game_to_catalog` automatically formats a complete rulebook document (`game_docs/<doc_id>.md`) and uploads it to Google Cloud Storage (`gs://board-game-host-media-401956137467/game_docs/`).
* **Semantic RAG Passage Retrieval (`search_board_game_rag_docs`)**: Answers complex rule, strategy, and setup questions by performing semantic chunk retrieval across the game document store.

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
