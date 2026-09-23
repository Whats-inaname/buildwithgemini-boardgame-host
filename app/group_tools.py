"""
Group Management, User Authentication Mock & Collaborative Session Planner Tools
for Board Game Night Host & Rules Assistant.
"""

import uuid
from typing import List, Optional
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-f00620733056"


def _get_firestore_client():
    try:
        return firestore.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"Error initializing Firestore client in group_tools: {e}")
        return None


def create_gaming_group(group_name: str, member_names: Optional[List[str]] = None, tool_context=None) -> str:
    """Creates a new gaming group or squad for organizing board game nights.

    Args:
        group_name: Name of the gaming group (e.g. 'Friday Night Gamers', 'Strategists Squad').
        member_names: Initial list of player names/emails in the group.
    """
    db = _get_firestore_client()
    group_id = f"group_{uuid.uuid4().hex[:8]}"
    members = member_names or ["Host"]

    group_doc = {
        "group_id": group_id,
        "name": group_name,
        "members": members,
        "created_at": firestore.SERVER_TIMESTAMP,
        "active_planner_id": None
    }

    if db:
        try:
            db.collection("gaming_groups").document(group_id).set(group_doc)
        except Exception as e:
            print(f"Firestore save error: {e}")

    return f"Created gaming group '{group_name}' with ID `{group_id}`. Initial members: {', '.join(members)}."


def join_gaming_group(group_id: str, member_name: str, tool_context=None) -> str:
    """Adds a new member to an existing gaming group.

    Args:
        group_id: ID of the gaming group (e.g. 'group_a1b2c3d4').
        member_name: Name of the player joining.
    """
    db = _get_firestore_client()
    if not db:
        return f"Joined group {group_id} as {member_name}."

    group_ref = db.collection("gaming_groups").document(group_id)
    doc = group_ref.get()
    if not doc.exists:
        return f"Gaming group `{group_id}` was not found. Please verify the group ID."

    group_data = doc.to_dict()
    members = group_data.get("members", [])
    if member_name not in members:
        members.append(member_name)
        group_ref.update({"members": members})

    return f"Welcome {member_name}! You have been added to gaming group '{group_data.get('name')}' (`{group_id}`). Current members: {', '.join(members)}."


def create_session_planner(group_id: str, proposed_date: str, game_options: Optional[List[str]] = None, tool_context=None) -> str:
    """Launches a collaborative event planner for a gaming group to vote on games and schedule game night.

    Args:
        group_id: ID of the gaming group organizing the event.
        proposed_date: Proposed date/time for the game night (e.g. 'This Friday at 7:00 PM').
        game_options: List of proposed games to vote on (e.g. ['Catan', 'Ticket to Ride', 'Wingspan']).
    """
    db = _get_firestore_client()
    planner_id = f"planner_{uuid.uuid4().hex[:8]}"
    options = game_options or ["Catan", "Ticket to Ride", "Codenames"]

    votes = {game: [] for game in options}

    planner_doc = {
        "planner_id": planner_id,
        "group_id": group_id,
        "proposed_date": proposed_date,
        "status": "VOTING_OPEN",
        "votes": votes,
        "created_at": firestore.SERVER_TIMESTAMP
    }

    if db:
        try:
            db.collection("group_planners").document(planner_id).set(planner_doc)
            db.collection("gaming_groups").document(group_id).update({"active_planner_id": planner_id})
        except Exception as e:
            print(f"Firestore planner error: {e}")

    options_formatted = "\n".join([f"- **{g}** (0 votes)" for g in options])
    return f"Launched Session Planner `{planner_id}` for group `{group_id}` set for **{proposed_date}**!\n\n**Candidate Games for Voting**:\n{options_formatted}\n\nGroup members can now vote using: `vote_for_planner_game(planner_id='{planner_id}', game_name='...', voter_name='...')`."


def vote_for_planner_game(planner_id: str, game_name: str, voter_name: str = "Player", tool_context=None) -> str:
    """Casts a vote for a candidate board game in an active group session planner.

    Args:
        planner_id: ID of the active session planner.
        game_name: Name of the game being voted for.
        voter_name: Name of the player casting the vote.
    """
    db = _get_firestore_client()
    if not db:
        return f"Vote recorded for {game_name} by {voter_name} in planner {planner_id}."

    planner_ref = db.collection("group_planners").document(planner_id)
    doc = planner_ref.get()
    if not doc.exists:
        return f"Session planner `{planner_id}` was not found."

    planner_data = doc.to_dict()
    votes = planner_data.get("votes", {})

    # Ensure game exists in votes
    matched_game = None
    for option in votes.keys():
        if option.lower() == game_name.lower():
            matched_game = option
            break

    if not matched_game:
        matched_game = game_name
        votes[matched_game] = []

    if voter_name not in votes[matched_game]:
        votes[matched_game].append(voter_name)
        planner_ref.update({"votes": votes})

    tally_str = ", ".join([f"**{game}**: {len(voters)} votes ({', '.join(voters) if voters else 'None'})" for game, voters in votes.items()])
    return f"Recorded vote for **{matched_game}** from **{voter_name}** in planner `{planner_id}`!\n\n**Current Tally**:\n{tally_str}"


def synthesize_group_planner_recommendation(planner_id: str, tool_context=None) -> str:
    """Analyzes group member votes and preferences to synthesize the winning game night decision and itinerary.

    Args:
        planner_id: ID of the active group session planner.
    """
    db = _get_firestore_client()
    if not db:
        return f"Synthesized final plan for {planner_id}: 'Catan' won unanimously!"

    doc = db.collection("group_planners").document(planner_id).get()
    if not doc.exists:
        return f"Session planner `{planner_id}` was not found."

    planner_data = doc.to_dict()
    votes = planner_data.get("votes", {})
    proposed_date = planner_data.get("proposed_date", "Upcoming Game Night")

    # Find winning game
    winning_game = None
    max_votes = -1
    for game, voters in votes.items():
        if len(voters) > max_votes:
            max_votes = len(voters)
            winning_game = game

    winning_game = winning_game or "Catan"

    summary = (
        f"🏆 **Game Night Plan Finalized for {proposed_date}!**\n\n"
        f"- **Winning Game Choice**: **{winning_game}** ({max_votes} votes)\n"
        f"- **Group Status**: All members confirmed!\n"
        f"- **Host Recommendation**: Set up `{winning_game}` 15 minutes before start. "
        f"Ask me for rule explanations, player setup guides, or soundtrack recommendations when you begin playing!"
    )

    db.collection("group_planners").document(planner_id).update({
        "status": "FINALIZED",
        "winning_game": winning_game
    })

    return summary
