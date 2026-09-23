"""User profile, location memory, and implicit personalization store backed by Cloud Firestore."""

import os
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-f00620733056")
USER_PROFILES_COLLECTION = "user_profiles"

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def set_user_profile(
    user_id: str = "web-user",
    home_city: str = "",
    favorite_categories: str = "",
    avoided_mechanics: str = "",
    preferred_player_count: int = 0,
) -> str:
    """Saves or updates a player's home location, favorite genres, avoided mechanics, and preferred player counts in Firestore.

    Args:
        user_id: Unique user or player ID (default 'web-user').
        home_city: Home city or location for implicit weather and venue lookup (e.g. 'Seattle, WA' or 'London, UK').
        favorite_categories: Comma-separated favorite genres/categories (e.g. 'Strategy, Deckbuilder, Sci-Fi').
        avoided_mechanics: Comma-separated mechanics or styles to avoid (e.g. 'Elimination, High Luck').
        preferred_player_count: Typical or preferred group size (e.g. 4).

    Returns:
        Confirmation message.
    """
    try:
        db = _get_db()
        data = {}
        if home_city:
            data["home_city"] = home_city
        if favorite_categories:
            data["favorite_categories"] = [c.strip() for c in favorite_categories.split(",") if c.strip()]
        if avoided_mechanics:
            data["avoided_mechanics"] = [m.strip() for m in avoided_mechanics.split(",") if m.strip()]
        if preferred_player_count > 0:
            data["preferred_player_count"] = preferred_player_count

        data["updated_at"] = firestore.SERVER_TIMESTAMP

        db.collection(USER_PROFILES_COLLECTION).document(user_id).set(data, merge=True)
        return (
            f"Updated player profile for '{user_id}'! "
            f"Location: {home_city or 'Unchanged'}. Favorites: {favorite_categories or 'Unchanged'}."
        )
    except Exception as e:
        return f"Error updating user profile: {e}"


def get_user_profile(user_id: str = "web-user") -> dict:
    """Fetches a player's saved profile, home location, and game preferences from Firestore.

    Args:
        user_id: Unique user or player ID.

    Returns:
        Dictionary of profile settings or default values.
    """
    try:
        db = _get_db()
        doc = db.collection(USER_PROFILES_COLLECTION).document(user_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception:
        pass
    return {
        "home_city": "San Francisco",
        "favorite_categories": ["Strategy"],
        "avoided_mechanics": [],
        "preferred_player_count": 4,
    }
