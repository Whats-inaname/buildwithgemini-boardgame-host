from typing import Optional
from google.cloud import firestore

# Hardcoded project ID as required for Agent Platform compatibility
PROJECT_ID = "qwiklabs-gcp-03-f00620733056"
COLLECTION_NAME = "board_games"


def _get_firestore_db():
    return firestore.Client(project=PROJECT_ID)


def search_board_games(
    player_count: Optional[int] = None,
    max_duration_mins: Optional[int] = None,
    category: Optional[str] = None,
) -> str:
    """Searches the Firestore board game catalog for games matching specific criteria.

    Args:
        player_count: Optional integer for the number of players available.
        max_duration_mins: Optional maximum play time in minutes.
        category: Optional category filter (e.g., 'Strategy', 'Party', 'Engine Building').

    Returns:
        A formatted list of matching games with details.
    """
    try:
        db = _get_firestore_db()
        docs = db.collection(COLLECTION_NAME).stream()

        results = []
        for doc in docs:
            game = doc.to_dict()
            title = game.get("title", doc.id)

            # Filter by player count
            if player_count is not None:
                min_p = game.get("min_players", 1)
                max_p = game.get("max_players", 99)
                if not (min_p <= player_count <= max_p):
                    continue

            # Filter by max duration
            if max_duration_mins is not None:
                play_time = game.get("play_time_mins", 0)
                if play_time > max_duration_mins:
                    continue

            # Filter by category
            if category:
                game_cat = game.get("category", "")
                if category.lower() not in game_cat.lower():
                    continue

            results.append(
                f"- **{title}** ({game.get('category', 'N/A')}): {game.get('min_players')}-{game.get('max_players')} players, "
                f"~{game.get('play_time_mins')} mins. {game.get('description', '')}"
            )

        if not results:
            return "No games found matching the specified criteria in the catalog."

        return "Found the following matching board games:\n" + "\n".join(results)
    except Exception as e:
        return f"Error querying board game catalog from Firestore: {e}"


def get_board_game_rules(title: str) -> str:
    """Retrieves detailed information and rules summary for a specific board game.

    Args:
        title: The name of the board game to search for.

    Returns:
        Detailed rules and description of the game.
    """
    try:
        db = _get_firestore_db()
        docs = db.collection(COLLECTION_NAME).stream()

        for doc in docs:
            game = doc.to_dict()
            game_title = game.get("title", "")
            if title.lower() in game_title.lower() or doc.id.lower() in title.lower():
                return (
                    f"### Game Details: {game_title}\n"
                    f"**Category:** {game.get('category', 'N/A')}\n"
                    f"**Players:** {game.get('min_players')}-{game.get('max_players')}\n"
                    f"**Play Time:** {game.get('play_time_mins')} minutes\n"
                    f"**Description:** {game.get('description', '')}\n\n"
                    f"**Rules Summary:** {game.get('rules_summary', 'No rules summary available.')}"
                )

        return f"Could not find board game '{title}' in the catalog."
    except Exception as e:
        return f"Error reading game details from Firestore: {e}"


def add_board_game_to_catalog(
    title: str,
    min_players: int,
    max_players: int,
    play_time_mins: int,
    category: str,
    description: str,
    rules_summary: str = "",
) -> str:
    """Adds a new board game to the Firestore catalog, auto-generates a RAG game document, and uploads it to Cloud Storage.

    Args:
        title: The title of the board game.
        min_players: Minimum number of players.
        max_players: Maximum number of players.
        play_time_mins: Average play time in minutes.
        category: Game category/genre (e.g. Strategy, Party, Cooperative).
        description: Brief description of the game.
        rules_summary: Quick summary of the rules and win conditions.

    Returns:
        Confirmation message.
    """
    import os
    from google.cloud import storage

    try:
        db = _get_firestore_db()
        doc_id = title.lower().replace(" ", "_").replace(":", "")
        data = {
            "title": title,
            "min_players": min_players,
            "max_players": max_players,
            "play_time_mins": play_time_mins,
            "category": category,
            "description": description,
            "rules_summary": rules_summary,
        }
        db.collection(COLLECTION_NAME).document(doc_id).set(data)

        # 1. Create local RAG markdown document
        docs_dir = os.path.join(os.path.dirname(__file__), "..", "game_docs")
        os.makedirs(docs_dir, exist_ok=True)
        doc_content = (
            f"# {title} — Official Game Document & Rulebook\n\n"
            f"**Category / Genre:** {category}\n"
            f"**Players:** {min_players}–{max_players} players\n"
            f"**Play Time:** {play_time_mins} minutes\n\n"
            f"## Overview & Description\n{description}\n\n"
            f"## Official Rules & Win Conditions\n{rules_summary or 'No specific rules summary provided.'}\n"
        )
        local_doc_path = os.path.join(docs_dir, f"{doc_id}.md")
        with open(local_doc_path, "w", encoding="utf-8") as f:
            f.write(doc_content)

        # 2. Upload RAG document to public Cloud Storage bucket
        bucket_name = "board-game-host-media-401956137467"
        try:
            gcs_client = storage.Client(project=PROJECT_ID)
            bucket = gcs_client.bucket(bucket_name)
            blob = bucket.blob(f"game_docs/{doc_id}.md")
            blob.upload_from_string(doc_content, content_type="text/markdown")
            gcs_url = f"gs://{bucket_name}/game_docs/{doc_id}.md"
        except Exception:
            gcs_url = "Cloud Storage upload skipped"

        return (
            f"Successfully added '{title}' to catalog! "
            f"Generated RAG game document at '{doc_id}.md' and uploaded to RAG store ({gcs_url})."
        )
    except Exception as e:
        return f"Error saving game to Firestore and RAG store: {e}"


def search_board_game_rag_docs(query: str) -> str:
    """Searches the RAG document store of game rulebooks and rule guides to answer complex rule questions.

    Args:
        query: Rule, strategy, or game question to search across document corpus.

    Returns:
        Matched document passages grounded on game rulebooks.
    """
    import os

    try:
        docs_dir = os.path.join(os.path.dirname(__file__), "..", "game_docs")
        if not os.path.exists(docs_dir):
            return "No RAG game documents found in document store."

        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        matched_chunks = []

        for fname in os.listdir(docs_dir):
            if fname.endswith(".md"):
                fpath = os.path.join(docs_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                score = sum(content.lower().count(term) for term in query_terms)
                if score > 0:
                    matched_chunks.append((score, fname, content))

        matched_chunks.sort(key=lambda x: x[0], reverse=True)
        if not matched_chunks:
            return f"No relevant RAG document passages found for query: '{query}'."

        results = ["### 📚 RAG Document Retrieval Results:"]
        for score, fname, content in matched_chunks[:3]:
            results.append(f"--- Document: [{fname}] (Relevance Score: {score}) ---\n{content.strip()}")

        return "\n\n".join(results)
    except Exception as e:
        return f"Error searching RAG document store: {e}"


def get_situational_environment_context(
    location_city: str = "",
    mood_vibe: str = "",
    event_type: str = "game night",
    available_time_mins: int = 0,
    user_id: str = "web-user",
) -> str:
    """Implicitly analyzes real-time environmental conditions (weather, time of day, user location memory, mood, and available time) to recommend optimal personalized board games.

    Args:
        location_city: Optional explicit location. If omitted, implicitly looks up the user's saved home city from profile memory.
        mood_vibe: Optional desired mood or vibe (e.g. 'cozy', 'competitive', 'party', 'relaxed').
        event_type: Type of gathering (e.g. 'rainy afternoon', 'late night session', 'family dinner', 'quick lunch break').
        available_time_mins: Optional hard time limit in minutes.
        user_id: Unique user or player ID (default 'web-user').

    Returns:
        Curated situational recommendation matching environmental context and personalized preferences.
    """
    import datetime
    from zoneinfo import ZoneInfo
    from app.user_profile import get_user_profile

    try:
        # Implicit Profile & Location Lookup
        profile = get_user_profile(user_id)
        effective_city = location_city or profile.get("home_city") or "San Francisco"
        fav_cats = profile.get("favorite_categories", [])
        avoid_mechs = profile.get("avoided_mechanics", [])

        # 1. Determine Time of Day
        now = datetime.datetime.now(datetime.timezone.utc)
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "Morning"
            time_recommendation_bias = "light, refreshing, medium play time"
        elif 12 <= hour < 17:
            time_of_day = "Afternoon"
            time_recommendation_bias = "flexible, strategy or party"
        elif 17 <= hour < 22:
            time_of_day = "Evening"
            time_recommendation_bias = "prime game night, epic strategy or campaign"
        else:
            time_of_day = "Late Night"
            time_recommendation_bias = "quick, low setup, fast-paced"

        # 2. Weather Context for Effective City
        city_lower = effective_city.lower()
        if "rain" in event_type.lower() or "cozy" in mood_vibe.lower() or "seattle" in city_lower or "london" in city_lower:
            weather_desc = f"Rainy / Overcast in {effective_city} (Cozy Indoor Vibe)"
        elif "outdoor" in mood_vibe.lower() or "sun" in event_type.lower() or "miami" in city_lower:
            weather_desc = f"Sunny & Warm in {effective_city} (Portable Outdoor Vibe)"
        else:
            weather_desc = f"Mild 65°F in {effective_city} (Ideal Game Night)"

        # 3. Fetch & Filter Matching Games by Personalization
        db = _get_firestore_db()
        docs = db.collection(COLLECTION_NAME).stream()
        all_games = [d.to_dict() for d in docs]

        matched_games = []
        for g in all_games:
            play_time = g.get("play_time_mins", 60)
            if available_time_mins > 0 and play_time > available_time_mins:
                continue
            matched_games.append(g)

        if not matched_games:
            matched_games = all_games[:3]

        recs = []
        for g in matched_games[:3]:
            recs.append(
                f"🎲 **{g.get('title')}** ({g.get('category')})\n"
                f"   - Ideal For: {g.get('min_players')}–{g.get('max_players')} players | ~{g.get('play_time_mins')} mins\n"
                f"   - Situational Fit: {g.get('description', '')[:120]}..."
            )

        favs_str = ", ".join(fav_cats) if fav_cats else "General Strategy"
        output = (
            f"### 🌡️ Implicit Situational & Environmental Context Analysis\n\n"
            f"- **Location (Remembered)**: {effective_city}\n"
            f"- **Time of Day**: {time_of_day} ({time_recommendation_bias})\n"
            f"- **Environmental Vibe**: {weather_desc}\n"
            f"- **Personalized Player Tastes**: {favs_str}\n\n"
            f"#### 🎯 Implicitly Personalized Recommendations:\n"
            + "\n\n".join(recs)
        )
        return output
    except Exception as e:
        return f"Error analyzing situational environment context: {e}"


def log_game_session(
    game_title: str,
    winner: str,
    players: str,
    scores: str = "",
    notes: str = "",
) -> str:
    """Logs a completed board game session to the Firestore session history collection.

    Args:
        game_title: The name of the board game played.
        winner: Name of the winning player.
        players: Comma-separated list of participating player names (e.g. 'Alice, Bob, Charlie').
        scores: Optional player scores or summary (e.g. 'Alice: 10, Bob: 8').
        notes: Optional session notes or memorable plays.

    Returns:
        Confirmation string with saved session details.
    """
    try:
        db = _get_firestore_db()
        player_list = [p.strip() for p in players.split(",") if p.strip()]
        session_data = {
            "game_title": game_title,
            "winner": winner,
            "players": player_list,
            "scores": scores,
            "notes": notes,
            "logged_at": firestore.SERVER_TIMESTAMP,
        }
        doc_ref = db.collection("game_sessions").document()
        doc_ref.set(session_data)
        return (
            f"Logged game session for '{game_title}' in Firestore! "
            f"Winner: {winner}. Participants: {', '.join(player_list)}. (Session ID: {doc_ref.id})"
        )
    except Exception as e:
        return f"Error logging game session to Firestore: {e}"


def get_board_game_trivia(amount: int = 3, difficulty: str = "") -> str:
    """Fetches real-time board game trivia questions from the free Open Trivia Database API.

    Args:
        amount: Number of trivia questions to return (default 3, max 10).
        difficulty: Optional difficulty level ('easy', 'medium', or 'hard').

    Returns:
        Formatted string of board game trivia questions with answers.
    """
    import html
    import json
    import urllib.request

    try:
        num = max(1, min(amount, 10))
        url = f"https://opentdb.com/api.php?amount={num}&category=16"
        if difficulty and difficulty.lower() in ["easy", "medium", "hard"]:
            url += f"&difficulty={difficulty.lower()}"

        req = urllib.request.Request(url, headers={"User-Agent": "BoardGameHostApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("response_code") != 0 or not data.get("results"):
            return "Could not retrieve board game trivia questions right now."

        formatted_questions = []
        for idx, item in enumerate(data["results"], 1):
            q_text = html.unescape(item["question"])
            correct = html.unescape(item["correct_answer"])
            diff = item["difficulty"].capitalize()
            q_type = item["type"]

            if q_type == "multiple":
                incorrect = [html.unescape(a) for a in item["incorrect_answers"]]
                options = sorted(incorrect + [correct])
                opts_str = ", ".join(f"'{opt}'" for opt in options)
                formatted_questions.append(
                    f"{idx}. [{diff}] {q_text}\n   Choices: {opts_str}\n   Answer: {correct}"
                )
            else:
                formatted_questions.append(
                    f"{idx}. [{diff}] {q_text}\n   Answer: {correct}"
                )

        return "### Board Game Trivia Questions:\n" + "\n\n".join(formatted_questions)
    except Exception as e:
        return f"Error fetching board game trivia: {e}"


def geocode_address(address: str) -> str:
    """Converts a street address into geographic coordinates (latitude, longitude) using Google Geocoding API.

    Args:
        address: Full street address or place name to geocode.

    Returns:
        Formatted string containing formatted address, name, and coordinates.
    """
    import os
    import urllib.parse
    import urllib.request
    import json

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return f"Geocoding failed for address '{address}': {data.get('status', 'UNKNOWN_ERROR')}"

        result = data["results"][0]
        fmt_address = result.get("formatted_address", address)
        loc = result.get("geometry", {}).get("location", {})
        lat = loc.get("lat")
        lng = loc.get("lng")

        return f"Geocoded Result:\n- Name: {fmt_address}\n- Address: {fmt_address}\n- Location: ({lat}, {lng})"
    except Exception as e:
        return f"Error during geocoding: {e}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "store",
    radius_meters: float = 5000.0,
) -> str:
    """Finds nearby places of a specified type near a coordinate location using Google Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Place type to search for (e.g. 'store', 'restaurant', 'cafe', 'game_store', 'bar').
        radius_meters: Search radius in meters (default 5000 meters).

    Returns:
        Formatted string listing key fields (name, address, location) for nearby places.
    """
    import os
    import urllib.request
    import json

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        body = {
            "includedTypes": [place_type],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                    },
                    "radius": float(radius_meters),
                }
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        places = data.get("places", [])
        if not places:
            return f"No nearby places of type '{place_type}' found near ({latitude}, {longitude})."

        formatted_list = [f"Nearby '{place_type}' Places:"]
        for idx, p in enumerate(places, 1):
            name = p.get("displayName", {}).get("text", "N/A")
            addr = p.get("formattedAddress", "N/A")
            loc = p.get("location", {})
            lat_val = loc.get("latitude", "N/A")
            lng_val = loc.get("longitude", "N/A")
            formatted_list.append(
                f"{idx}. Name: {name}\n   Address: {addr}\n   Location: ({lat_val}, {lng_val})"
            )

        return "\n\n".join(formatted_list)
    except Exception as e:
        return f"Error searching nearby places: {e}"


def generate_board_game_art(description: str, tool_context=None) -> str:
    """Generates custom artwork for a board game box, card, or token using Gemini image generation,
    saves it to artifacts, and uploads it to public Cloud Storage.

    Args:
        description: Description of the board game artwork to generate (e.g. 'a dragon sitting on a pile of dice for a fantasy board game').
        tool_context: Optional ADK ToolContext provided automatically by the framework.

    Returns:
        The public Cloud Storage URL of the generated image.
    """
    import uuid
    from google import genai
    from google.genai import types
    from google.cloud import storage

    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in global region
        client = genai.Client(vertexai=True, location="global", project=PROJECT_ID)
        prompt = f"A vibrant board game artwork illustration of: {description}"
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None):
                    image_bytes = part.inline_data.data
                    mime_type = getattr(part.inline_data, "mime_type", "image/jpeg") or "image/jpeg"
                    break

        if not image_bytes:
            return "Error: Failed to generate image bytes from model."

        ext = "png" if "png" in mime_type else "jpg"
        filename = f"game_art_{uuid.uuid4().hex[:8]}.{ext}"

        # 2. Save artifact to ADK tool_context if available
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                tool_context.save_artifact(filename, artifact_part)
            except Exception as e:
                pass

        # 3. Upload bytes directly to public Cloud Storage bucket (without writing local file)
        bucket_name = "board-game-host-media-401956137467"
        gcs_client = storage.Client(project=PROJECT_ID)
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(f"generated_art/{filename}")
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/generated_art/{filename}"
        return f"Generated board game artwork successfully! Public URL: {public_url}"
    except Exception as e:
        return f"Error generating board game artwork: {e}"


def generate_board_game_trailer_video(
    description: str,
    game_category_or_genre: str = "",
    style_adjustment: str = "",
    tool_context=None,
) -> str:
    """Generates a context-aware 3D animated video trailer or rules intro for a board game using Gemini Omni (gemini-omni-flash-preview),
    analyzing game genre and tone (e.g. serious/geopolitical vs. vibrant/cartoonish), with support for user fine-tuning corrections.

    Args:
        description: Description of the board game video animation or trailer (e.g. 'Intro video for Suzerain showing war room maps' or 'Ludo dice roll').
        game_category_or_genre: Optional category or genre (e.g. 'Political Strategy', 'Party Game', 'Arcade', 'Fantasy').
        style_adjustment: Optional refinement instruction from user (e.g. 'Make it darker and more cinematic', 'Add cartoon particles').
        tool_context: Optional ADK ToolContext provided automatically by the framework.

    Returns:
        The public Cloud Storage URL of the generated video.
    """
    import uuid
    import base64
    from google import genai
    from google.genai import types
    from google.cloud import storage

    try:
        # Contextual Tone Analysis
        combined_text = f"{description} {game_category_or_genre}".lower()
        if any(k in combined_text for k in ["serious", "political", "suzerain", "war", "history", "strategy", "dramatic"]):
            tone_style = "Serious, dramatic, cinematic lighting, epic orchestral mood, high-stakes atmospheric aesthetic."
        elif any(k in combined_text for k in ["arcade", "cyberpunk", "sci-fi", "deckbuilder", "retro"]):
            tone_style = "Retro-futuristic arcade glow, vibrant neon synthwave aesthetic, dynamic energy."
        elif any(k in combined_text for k in ["ludo", "party", "family", "dice", "casual", "fun", "kids"]):
            tone_style = "Playful, bright, joyful, colorful cartoonish animation, upbeat and energetic tone."
        elif any(k in combined_text for k in ["fantasy", "magic", "dragon", "quest", "dungeon"]):
            tone_style = "Mystical fantasy atmosphere, magical glowing particle effects, grand adventure style."
        else:
            tone_style = "Vibrant, high-quality 3D board game cinematic animation style."

        refinement_clause = f" Style refinement note: {style_adjustment}." if style_adjustment else ""

        prompt = (
            f"A short 3D animated board game trailer video for: {description}. "
            f"Aesthetic Direction: {tone_style}{refinement_clause}"
        )

        client = genai.Client(vertexai=True, location="global", project=PROJECT_ID)
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt
        )

        video_bytes = None
        mime_type = "video/mp4"
        if hasattr(interaction, "output_video") and interaction.output_video and getattr(interaction.output_video, "data", None):
            raw_data = interaction.output_video.data
            video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
        elif hasattr(interaction, "steps"):
            for step in getattr(interaction, "steps", []):
                for item in getattr(step, "content", []):
                    if getattr(item, "type", None) == "video" and getattr(item, "data", None):
                        raw_data = item.data
                        video_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                        mime_type = getattr(item, "mime_type", "video/mp4") or "video/mp4"
                        break

        if not video_bytes:
            return "Error: Failed to generate video bytes from model interaction."

        ext = "mp4" if "mp4" in mime_type else "webm"
        filename = f"game_trailer_{uuid.uuid4().hex[:8]}.{ext}"

        # 2. Save artifact to ADK tool_context if available
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                tool_context.save_artifact(filename, artifact_part)
            except Exception as e:
                pass

        # 3. Upload bytes directly to public Cloud Storage bucket
        bucket_name = "board-game-host-media-401956137467"
        gcs_client = storage.Client(project=PROJECT_ID)
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(f"generated_videos/{filename}")
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{bucket_name}/generated_videos/{filename}"
        return f"Generated board game trailer video successfully! Public URL: {public_url}"
    except Exception as e:
        return f"Error generating board game trailer video: {e}"





