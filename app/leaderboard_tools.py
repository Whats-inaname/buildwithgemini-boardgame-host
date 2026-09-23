"""Game Night Leaderboards and ELO Tournament Tracking system backed by Cloud Firestore."""

import os
import math
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-f00620733056")
LEADERBOARD_COLLECTION = "squad_leaderboards"

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def record_game_match_result(
    group_name: str,
    winning_player: str,
    losing_players: str,
    game_title: str = "Board Game",
) -> str:
    """Records the match result for a game session, calculates ELO rating updates, and updates win streaks for squad members.

    Args:
        group_name: Name of the gaming squad (e.g. 'Friday Night Strategists').
        winning_player: Name or handle of the winning player (e.g. 'Alice').
        losing_players: Comma-separated list of losing players (e.g. 'Bob, Charlie, Dave').
        game_title: Title of the game played (e.g. 'Catan').

    Returns:
        Summary of ELO rating changes and updated squad leaderboard.
    """
    try:
        db = _get_db()
        group_id = group_name.lower().replace(" ", "_")
        losers = [p.strip() for p in losing_players.split(",") if p.strip() and p.strip() != winning_player]
        all_players = [winning_player] + losers

        doc_ref = db.collection(LEADERBOARD_COLLECTION).document(group_id)
        doc = doc_ref.get()
        players_data = doc.to_dict().get("players", {}) if doc.exists else {}

        # Ensure default stats exist for all players
        for p in all_players:
            if p not in players_data:
                players_data[p] = {
                    "player_name": p,
                    "elo": 1200,
                    "wins": 0,
                    "losses": 0,
                    "win_streak": 0,
                    "total_games": 0,
                }

        # Calculate ELO updates
        # Average ELO of opponents
        winner_elo = players_data[winning_player]["elo"]
        loser_elos = [players_data[l]["elo"] for l in losers]
        avg_opponent_elo = sum(loser_elos) / len(loser_elos) if loser_elos else 1200

        # Expected score for winner: E_A = 1 / (1 + 10^((ELO_B - ELO_A)/400))
        expected_winner = 1.0 / (1.0 + math.pow(10, (avg_opponent_elo - winner_elo) / 400.0))
        k_factor = 32
        winner_elo_gain = round(k_factor * (1.0 - expected_winner))

        # Update winner stats
        players_data[winning_player]["elo"] += winner_elo_gain
        players_data[winning_player]["wins"] += 1
        players_data[winning_player]["win_streak"] += 1
        players_data[winning_player]["total_games"] += 1

        # Update loser stats
        loser_loss = max(1, round(winner_elo_gain / max(1, len(losers))))
        for l in losers:
            players_data[l]["elo"] = max(800, players_data[l]["elo"] - loser_loss)
            players_data[l]["losses"] += 1
            players_data[l]["win_streak"] = 0
            players_data[l]["total_games"] += 1

        doc_ref.set({"group_name": group_name, "players": players_data}, merge=True)

        summary_lines = [
            f"🏆 **Match Result Recorded for '{group_name}'!**",
            f"🎮 Game Played: **{game_title}**",
            f"🥇 Winner: **{winning_player}** (+{winner_elo_gain} ELO | Total ELO: {players_data[winning_player]['elo']} | 🔥 Streak: {players_data[winning_player]['win_streak']})",
            f"🥈 Participants: {', '.join([f'{l} (-{loser_loss} ELO)' for l in losers])}",
        ]
        return "\n".join(summary_lines)
    except Exception as e:
        return f"Error recording match result for leaderboard: {e}"


def get_squad_leaderboard(group_name: str) -> str:
    """Retrieves the ELO leaderboard, win streaks, and champion rankings for a gaming squad.

    Args:
        group_name: Name of the gaming squad (e.g. 'Friday Night Strategists').

    Returns:
        Formatted squad leaderboard with ELO rankings and trophies.
    """
    try:
        db = _get_db()
        group_id = group_name.lower().replace(" ", "_")
        doc = db.collection(LEADERBOARD_COLLECTION).document(group_id).get()

        if not doc.exists:
            return f"No match records or leaderboard found for gaming squad '{group_name}' yet. Record a game result first!"

        data = doc.to_dict()
        players = list(data.get("players", {}).values())
        players.sort(key=lambda x: x.get("elo", 1200), reverse=True)

        trophies = ["🥇", "🥈", "🥉"]
        rows = []
        for idx, p in enumerate(players):
            badge = trophies[idx] if idx < 3 else f"#{idx+1}"
            streak_badge = f" 🔥{p.get('win_streak')} Streak!" if p.get('win_streak', 0) >= 2 else ""
            win_rate = round((p.get("wins", 0) / max(1, p.get("total_games", 1))) * 100, 1)
            rows.append(
                f"{badge} **{p.get('player_name')}** — **{p.get('elo')} ELO** "
                f"({p.get('wins')}W - {p.get('losses')}L | {win_rate}% Win Rate){streak_badge}"
            )

        return (
            f"🏆 **Gaming Squad Leaderboard: '{group_name}'** 🏆\n\n"
            + "\n".join(rows)
        )
    except Exception as e:
        return f"Error fetching squad leaderboard: {e}"
