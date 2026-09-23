import os
import subprocess
from google.cloud import firestore
from google.oauth2.credentials import Credentials

# Hardcoded project ID as required to prevent Agent Platform project number issues
PROJECT_ID = "qwiklabs-gcp-03-f00620733056"
COLLECTION_NAME = "board_games"

INITIAL_GAMES = [
    {
        "id": "catan",
        "title": "Catan",
        "min_players": 3,
        "max_players": 4,
        "play_time_mins": 75,
        "category": "Strategy",
        "description": "Trade, build, and settle the island of Catan.",
        "rules_summary": "Players collect resource cards (wood, brick, sheep, wheat, ore) based on dice rolls to build roads, settlements, and cities. First player to 10 victory points wins."
    },
    {
        "id": "ticket_to_ride",
        "title": "Ticket to Ride",
        "min_players": 2,
        "max_players": 5,
        "play_time_mins": 60,
        "category": "Family Strategy",
        "description": "Cross-country train adventure game where players claim railway routes across North America.",
        "rules_summary": "Collect train cards to claim railway routes on the map. Longest continuous path and completed destination tickets earn bonus points."
    },
    {
        "id": "codenames",
        "title": "Codenames",
        "min_players": 4,
        "max_players": 8,
        "play_time_mins": 15,
        "category": "Party Word Game",
        "description": "Social word game where two spymasters give one-word clues to help their team guess secret agent cards.",
        "rules_summary": "Spymasters give a one-word clue and a number. Teammates try to contact their agents while avoiding civilian cards and the assassin."
    },
    {
        "id": "wingspan",
        "title": "Wingspan",
        "min_players": 1,
        "max_players": 5,
        "play_time_mins": 70,
        "category": "Engine Building",
        "description": "Bird enthusiast card-driven engine-building game.",
        "rules_summary": "Attract birds to your wildlife preserves. Each bird extends a chain of powerful combinations across feeding, egg laying, and card drawing."
    },
    {
        "id": "splendor",
        "title": "Splendor",
        "min_players": 2,
        "max_players": 4,
        "play_time_mins": 30,
        "category": "Engine Building",
        "description": "Fast-paced chip-collecting and card development game of Renaissance gem merchants.",
        "rules_summary": "Collect gem tokens to buy gem mine cards, which provide permanent gem discounts and prestige points. First to 15 points triggers game end."
    }
]


def get_firestore_client():
    try:
        # Try default client first
        return firestore.Client(project=PROJECT_ID)
    except Exception:
        pass
    # Fallback to gcloud token if default ADC lacks permissions in local dev environment
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()
    creds = Credentials(token)
    return firestore.Client(project=PROJECT_ID, credentials=creds)


def seed_database():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    for game in INITIAL_GAMES:
        doc_id = game["id"]
        data = {k: v for k, v in game.items() if k != "id"}
        collection_ref.document(doc_id).set(data)
        print(f"Seeded game: {game['title']} (doc_id: {doc_id})")

    print(f"Successfully seeded {len(INITIAL_GAMES)} games into '{COLLECTION_NAME}' collection.")


if __name__ == "__main__":
    seed_database()
