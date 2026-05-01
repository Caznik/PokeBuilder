# src/api/services/saved_team_service.py
"""CRUD service for persisting and retrieving saved teams."""

import json
from typing import Any

from ..models.saved_team import SavedTeamDetail, SavedTeamMember, SavedTeamSummary
from ..models.team import CoverageResult, TeamAnalysisResponse, TeamMemberInput
from ..models.scoring import ScoreBreakdown, ScoreComponent
from .team_loader import load_team
from .team_analysis import analyze_team
from .team_scorer import score_team


def _parse_analysis(raw: dict) -> TeamAnalysisResponse:
    return TeamAnalysisResponse(
        valid=raw["valid"],
        issues=raw["issues"],
        roles=raw["roles"],
        weaknesses=raw["weaknesses"],
        resistances=raw["resistances"],
        coverage=CoverageResult(**raw["coverage"]),
        speed_control_archetype=raw.get("speed_control_archetype", "none"),
    )


def _parse_breakdown(raw: dict) -> ScoreBreakdown:
    return ScoreBreakdown(
        coverage=ScoreComponent(**raw["coverage"]),
        defensive=ScoreComponent(**raw["defensive"]),
        role=ScoreComponent(**raw["role"]),
        speed_control=ScoreComponent(**raw["speed_control"]),
        lead_pair=ScoreComponent(**raw["lead_pair"]),
    )


def _load_members(cur: Any, team_id: int) -> list[SavedTeamMember]:
    cur.execute(
        """
        SELECT stm.slot, stm.pokemon_name, stm.set_id,
               cs.name   AS set_name,
               n.name    AS nature,
               a.name    AS ability
        FROM   saved_team_members stm
        LEFT JOIN competitive_sets cs ON stm.set_id   = cs.id
        LEFT JOIN natures           n  ON cs.nature_id  = n.id
        LEFT JOIN abilities         a  ON cs.ability_id = a.id
        WHERE  stm.team_id = %s
        ORDER BY stm.slot
        """,
        (team_id,),
    )
    return [
        SavedTeamMember(
            slot=r[0], pokemon_name=r[1], set_id=r[2],
            set_name=r[3], nature=r[4], ability=r[5],
        )
        for r in cur.fetchall()
    ]


def save_team(
    conn: Any,
    name: str,
    members: list[TeamMemberInput],
    score: float,
    breakdown: ScoreBreakdown,
    analysis: TeamAnalysisResponse,
) -> SavedTeamDetail:
    """Insert a new saved team and its 6 member rows.

    Args:
        conn: Active psycopg2 connection.
        name: User-given label for the team.
        members: Ordered list of exactly 6 team members.
        score: Team score snapshot.
        breakdown: Score breakdown snapshot.
        analysis: Full team analysis snapshot.

    Returns:
        The newly created SavedTeamDetail.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO saved_teams (name, score, breakdown, analysis)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, score, created_at
            """,
            (name, score, json.dumps(breakdown.model_dump()), json.dumps(analysis.model_dump())),
        )
        row = cur.fetchone()
        team_id = row[0]

        for slot, member in enumerate(members):
            cur.execute(
                "INSERT INTO saved_team_members (team_id, slot, pokemon_name, set_id) VALUES (%s, %s, %s, %s)",
                (team_id, slot, member.pokemon_name, member.set_id),
            )

    conn.commit()

    with conn.cursor() as cur:
        saved_members = _load_members(cur, team_id)

    return SavedTeamDetail(
        id=row[0], name=row[1], score=float(row[2]), created_at=row[3],
        members=saved_members, breakdown=breakdown, analysis=analysis,
    )


def list_teams(conn: Any) -> list[SavedTeamSummary]:
    """Return all saved teams ordered by creation date descending (summary only).

    Args:
        conn: Active psycopg2 connection.

    Returns:
        List of SavedTeamSummary, newest first.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, score, created_at FROM saved_teams ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        return [
            SavedTeamSummary(
                id=row[0], name=row[1], score=float(row[2]), created_at=row[3],
                members=_load_members(cur, row[0]),
            )
            for row in rows
        ]


def get_team(conn: Any, team_id: int) -> SavedTeamDetail:
    """Fetch a single saved team with full analysis.

    Args:
        conn: Active psycopg2 connection.
        team_id: Primary key of the saved team.

    Returns:
        SavedTeamDetail with members, breakdown, and analysis.

    Raises:
        ValueError: If no team with that id exists.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, score, created_at, breakdown, analysis FROM saved_teams WHERE id = %s",
            (team_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Saved team {team_id} not found")
        members = _load_members(cur, team_id)

    return SavedTeamDetail(
        id=row[0], name=row[1], score=float(row[2]), created_at=row[3],
        breakdown=_parse_breakdown(row[4]),
        analysis=_parse_analysis(row[5]),
        members=members,
    )


def update_team(
    conn: Any,
    team_id: int,
    *,
    name: str | None = None,
    score: float | None = None,
    breakdown: ScoreBreakdown | None = None,
    analysis: TeamAnalysisResponse | None = None,
) -> SavedTeamDetail:
    """Update team name and/or snapshot fields.

    Args:
        conn: Active psycopg2 connection.
        team_id: Primary key of the saved team.
        name: New name, or None to leave unchanged.
        score: New score snapshot, or None to leave unchanged.
        breakdown: New breakdown snapshot, or None to leave unchanged.
        analysis: New analysis snapshot, or None to leave unchanged.

    Returns:
        Updated SavedTeamDetail.

    Raises:
        ValueError: If no team with that id exists.
    """
    sets = []
    values: list[Any] = []
    if name is not None:
        sets.append("name = %s"); values.append(name)
    if score is not None:
        sets.append("score = %s"); values.append(score)
    if breakdown is not None:
        sets.append("breakdown = %s"); values.append(json.dumps(breakdown.model_dump()))
    if analysis is not None:
        sets.append("analysis = %s"); values.append(json.dumps(analysis.model_dump()))

    if sets:
        values.append(team_id)
        with conn.cursor() as cur:
            cur.execute(f"UPDATE saved_teams SET {', '.join(sets)} WHERE id = %s", values)
        conn.commit()

    return get_team(conn, team_id)


def update_member(
    conn: Any,
    team_id: int,
    slot: int,
    pokemon_name: str,
    set_id: int,
) -> SavedTeamDetail:
    """Swap one member slot and re-score the full team.

    Args:
        conn: Active psycopg2 connection.
        team_id: Primary key of the saved team.
        slot: Member index 0-5 to replace.
        pokemon_name: New Pokemon name.
        set_id: New competitive set id.

    Returns:
        Updated SavedTeamDetail with fresh score, breakdown, and analysis.

    Raises:
        ValueError: If no team with that id exists, or the new set_id is invalid.
    """
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE saved_team_members SET pokemon_name = %s, set_id = %s WHERE team_id = %s AND slot = %s",
            (pokemon_name, set_id, team_id, slot),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Saved team {team_id} not found or slot {slot} invalid")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT slot, pokemon_name, set_id FROM saved_team_members WHERE team_id = %s ORDER BY slot",
            (team_id,),
        )
        rows = cur.fetchall()

    if not rows:
        raise ValueError(f"Saved team {team_id} not found")

    raw_members = [{"pokemon_name": r[1], "set_id": r[2]} for r in rows]
    builds = load_team(conn, raw_members)
    report = analyze_team(builds)
    scored = score_team(report, builds)

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE saved_teams SET score = %s, breakdown = %s, analysis = %s WHERE id = %s",
            (scored["score"], json.dumps(scored["breakdown"]), json.dumps(report), team_id),
        )

    conn.commit()
    return get_team(conn, team_id)


def delete_team(conn: Any, team_id: int) -> None:
    """Delete a saved team and cascade-remove its members.

    Args:
        conn: Active psycopg2 connection.
        team_id: Primary key of the saved team.

    Raises:
        ValueError: If no team with that id exists.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM saved_teams WHERE id = %s", (team_id,))
        if cur.rowcount == 0:
            raise ValueError(f"Saved team {team_id} not found")
    conn.commit()
