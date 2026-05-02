"""Unit tests for saved_team_service."""
import pytest
from src.api.models.saved_team import (
    SaveTeamRequest,
    UpdateTeamRequest,
    UpdateMemberRequest,
    SavedTeamMember,
    SavedTeamSummary,
    SavedTeamDetail,
)

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.api.models.team import TeamMemberInput, TeamAnalysisResponse, CoverageResult, PokemonBuild
from src.api.models.scoring import ScoreBreakdown, ScoreComponent
from src.api.services.saved_team_service import (
    save_team,
    list_teams,
    get_team,
    update_team,
    update_member,
    delete_team,
)

_NOW = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)

_FAKE_BUILD = PokemonBuild(
    pokemon_name="garchomp", set_id=1,
    types=["dragon"], nature="jolly", ability="rough-skin",
    item="Choice Scarf",
    stats={"hp": 357, "attack": 333, "defense": 251,
           "sp_attack": 167, "sp_defense": 206, "speed": 333},
    moves=[],
    evs={"hp": 4, "attack": 252, "defense": 0,
         "sp_attack": 0, "sp_defense": 0, "speed": 252},
)

_MEMBERS = [
    TeamMemberInput(pokemon_name="garchomp",   set_id=1),
    TeamMemberInput(pokemon_name="ferrothorn", set_id=2),
    TeamMemberInput(pokemon_name="rotom-wash", set_id=3),
    TeamMemberInput(pokemon_name="clefable",   set_id=4),
    TeamMemberInput(pokemon_name="heatran",    set_id=5),
    TeamMemberInput(pokemon_name="landorus",   set_id=6),
]

_SCORE_COMPONENT = ScoreComponent(score=1.0, reason="test")
_BREAKDOWN = ScoreBreakdown(
    coverage=_SCORE_COMPONENT,
    defensive=_SCORE_COMPONENT,
    role=_SCORE_COMPONENT,
    speed_control=_SCORE_COMPONENT,
    lead_pair=_SCORE_COMPONENT,
)
_ANALYSIS = TeamAnalysisResponse(
    valid=True,
    issues=[],
    roles={"physical_sweeper": 2},
    weaknesses={"ice": 1},
    resistances={"steel": 2},
    coverage=CoverageResult(covered_types=["fire"], missing_types=["fairy"]),
    speed_control_archetype="tailwind",
)

def _make_conn(fetchone_return=None, fetchall_return=None, rowcount=1):
    """Return a mock psycopg2 connection with a context-managed cursor."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return or []
    mock_cursor.rowcount = rowcount
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


class TestSaveTeam:
    def test_returns_saved_team_detail(self):
        member_rows = [(i, m.pokemon_name, m.set_id, None, None, None, None, None, None, None) for i, m in enumerate(_MEMBERS)]
        mock_conn, mock_cursor = _make_conn(
            fetchone_return=(1, "My Team", 8.5, _NOW),
            fetchall_return=member_rows,
        )
        with patch("src.api.services.saved_team_service.load_build", return_value=_FAKE_BUILD):
            result = save_team(mock_conn, "My Team", _MEMBERS, 8.5, _BREAKDOWN, _ANALYSIS)
        assert isinstance(result, SavedTeamDetail)
        assert result.id == 1
        assert result.name == "My Team"
        assert result.score == 8.5
        assert len(result.members) == 6

    def test_inserts_six_member_rows(self):
        mock_conn, mock_cursor = _make_conn(
            fetchone_return=(1, "My Team", 8.5, _NOW)
        )
        with patch("src.api.services.saved_team_service.load_build", return_value=_FAKE_BUILD):
            save_team(mock_conn, "My Team", _MEMBERS, 8.5, _BREAKDOWN, _ANALYSIS)
        # 1 INSERT saved_teams + 6 INSERTs members + 1 SELECT for _load_members
        assert mock_cursor.execute.call_count == 8

    def test_commits_transaction(self):
        mock_conn, mock_cursor = _make_conn(
            fetchone_return=(1, "My Team", 8.5, _NOW)
        )
        with patch("src.api.services.saved_team_service.load_build", return_value=_FAKE_BUILD):
            save_team(mock_conn, "My Team", _MEMBERS, 8.5, _BREAKDOWN, _ANALYSIS)
        mock_conn.commit.assert_called_once()


class TestListTeams:
    def test_returns_list_of_summaries(self):
        member_rows = [(i, f"pokemon{i}", i + 1, f"set{i}", "jolly", "ability", None, None, None, None) for i in range(6)]
        mock_conn, mock_cursor = _make_conn(
            fetchall_return=[(1, "Team A", 8.5, _NOW), (2, "Team B", 7.0, _NOW)]
        )
        mock_cursor.fetchall.side_effect = [
            [(1, "Team A", 8.5, _NOW), (2, "Team B", 7.0, _NOW)],
            member_rows,
            member_rows,
        ]
        result = list_teams(mock_conn)
        assert len(result) == 2
        assert all(isinstance(t, SavedTeamSummary) for t in result)
        assert result[0].name == "Team A"

    def test_empty_returns_empty_list(self):
        mock_conn, mock_cursor = _make_conn(fetchall_return=[])
        mock_cursor.fetchall.side_effect = [[]]
        result = list_teams(mock_conn)
        assert result == []


class TestGetTeam:
    def test_returns_detail_when_found(self):
        analysis_json = _ANALYSIS.model_dump()
        breakdown_json = _BREAKDOWN.model_dump()
        member_rows = [
            (0, "garchomp",   1, "Choice Scarf", "jolly",   "rough-skin", None, None, None, None),
            (1, "ferrothorn", 2, "Defensive",    "relaxed", "iron-barbs", None, None, None, None),
            (2, "rotom-wash", 3, "Defensive",    "bold",    "levitate",   None, None, None, None),
            (3, "clefable",   4, "Calm Mind",    "calm",    "magic-guard",None, None, None, None),
            (4, "heatran",    5, "Stealth Rock", "timid",   "flash-fire", None, None, None, None),
            (5, "landorus",   6, "Scarf",        "jolly",   "intimidate", None, None, None, None),
        ]
        mock_conn, mock_cursor = _make_conn()
        mock_cursor.fetchone.return_value = (1, "My Team", 8.5, _NOW, breakdown_json, analysis_json)
        mock_cursor.fetchall.return_value = member_rows
        result = get_team(mock_conn, 1)
        assert isinstance(result, SavedTeamDetail)
        assert result.id == 1
        assert len(result.members) == 6

    def test_raises_value_error_when_not_found(self):
        mock_conn, mock_cursor = _make_conn(fetchone_return=None)
        with pytest.raises(ValueError, match="not found"):
            get_team(mock_conn, 999)


class TestUpdateTeam:
    def test_updates_name(self):
        analysis_json = _ANALYSIS.model_dump()
        breakdown_json = _BREAKDOWN.model_dump()
        member_rows = [
            (i, f"pokemon{i}", i + 1, None, None, None, None, None, None, None) for i in range(6)
        ]
        mock_conn, mock_cursor = _make_conn()
        mock_cursor.fetchone.return_value = (1, "New Name", 8.5, _NOW, breakdown_json, analysis_json)
        mock_cursor.fetchall.return_value = member_rows
        result = update_team(mock_conn, 1, name="New Name")
        assert result.name == "New Name"

    def test_raises_value_error_when_not_found(self):
        mock_conn, mock_cursor = _make_conn(fetchone_return=None)
        with pytest.raises(ValueError, match="not found"):
            update_team(mock_conn, 999, name="Ghost")


class TestUpdateMember:
    def test_updates_slot_without_rescoring(self):
        from src.api.models.saved_team import UpdateMemberRequest
        analysis_dict = _ANALYSIS.model_dump()
        breakdown_dict = _BREAKDOWN.model_dump()
        member_rows = [
            (0, "rillaboom",  7, "Band",          "adamant", "grassy-surge", None, None, None, None),
            (1, "ferrothorn", 2, "Defensive",      "relaxed", "iron-barbs",   None, None, None, None),
            (2, "rotom-wash", 3, "Defensive",      "bold",    "levitate",     None, None, None, None),
            (3, "clefable",   4, "Calm Mind",      "calm",    "magic-guard",  None, None, None, None),
            (4, "heatran",    5, "Stealth Rock",   "timid",   "flash-fire",   None, None, None, None),
            (5, "landorus",   6, "Scarf",          "jolly",   "intimidate",   None, None, None, None),
        ]

        mock_conn, mock_cursor = _make_conn()
        mock_cursor.fetchall.return_value = member_rows
        mock_cursor.fetchone.return_value = (1, "My Team", 8.0, _NOW, breakdown_dict, analysis_dict)

        req = UpdateMemberRequest(pokemon_name="rillaboom", set_id=7)
        result = update_member(mock_conn, 1, slot=0, request=req)

        assert isinstance(result, SavedTeamDetail)

    def test_raises_value_error_when_team_not_found(self):
        from src.api.models.saved_team import UpdateMemberRequest
        mock_conn, mock_cursor = _make_conn(fetchone_return=None, rowcount=0)
        req = UpdateMemberRequest(pokemon_name="rillaboom", set_id=7)
        with pytest.raises(ValueError, match="not found"):
            update_member(mock_conn, 999, slot=0, request=req)


class TestDeleteTeam:
    def test_executes_delete(self):
        mock_conn, mock_cursor = _make_conn()
        delete_team(mock_conn, 1)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_raises_value_error_when_not_found(self):
        mock_conn, mock_cursor = _make_conn(rowcount=0)
        with pytest.raises(ValueError, match="not found"):
            delete_team(mock_conn, 999)


def test_save_team_populates_member_detail_columns():
    """save_team writes item/evs/moves/nature/ability from load_build into new columns."""
    from src.api.services.saved_team_service import save_team
    from src.api.models.team import PokemonBuild, MoveDetail, TeamMemberInput
    from src.api.models.scoring import ScoreBreakdown, ScoreComponent
    from src.api.models.team import TeamAnalysisResponse, CoverageResult
    import json

    _sc = ScoreComponent(score=1.0, reason="test")
    _bd = ScoreBreakdown(
        coverage=_sc, defensive=_sc, role=_sc,
        speed_control=_sc, lead_pair=_sc,
    )
    _an = TeamAnalysisResponse(
        valid=True, issues=[], roles={}, weaknesses={}, resistances={},
        coverage=CoverageResult(covered_types=[], missing_types=[]),
    )

    members = [TeamMemberInput(pokemon_name=f"poke{i}", set_id=i) for i in range(6)]

    fake_build = PokemonBuild(
        pokemon_name="poke0", set_id=0,
        types=["normal"], nature="jolly", ability="keen-eye",
        item="Choice Scarf",
        stats={"hp": 300, "attack": 200, "defense": 150,
               "sp_attack": 100, "sp_defense": 120, "speed": 180},
        moves=[MoveDetail("tackle", "normal", "physical")],
        evs={"hp": 4, "attack": 252, "defense": 0,
             "sp_attack": 0, "sp_defense": 0, "speed": 252},
    )

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cur.fetchone.side_effect = [(1, "My Team", 8.5, "2026-05-02")]
    cur.fetchall.return_value = [
        (i, f"poke{i}", i, None, "jolly", "keen-eye",
         "Choice Scarf", None,
         {"hp": 4, "attack": 252, "defense": 0,
          "sp_attack": 0, "sp_defense": 0, "speed": 252},
         ["tackle", "", "", ""])
        for i in range(6)
    ]

    with patch(
        "src.api.services.saved_team_service.load_build",
        return_value=fake_build,
    ) as mock_load:
        save_team(conn, "My Team", members, 8.5, _bd, _an)

    # load_build called once per member
    assert mock_load.call_count == 6

    # Verify the INSERT used the new columns
    insert_calls = [
        c for c in cur.execute.call_args_list
        if "INSERT INTO saved_team_members" in str(c)
    ]
    assert len(insert_calls) == 6

    first_call_sql = str(insert_calls[0])
    assert "item" in first_call_sql
    assert "nature_override" in first_call_sql


def test_update_member_patches_item_without_rescoring():
    """update_member writes override fields and does not call score_team."""
    from src.api.services.saved_team_service import update_member
    from src.api.models.saved_team import UpdateMemberRequest, SavedTeamDetail, SavedTeamMember
    from src.api.models.scoring import ScoreBreakdown, ScoreComponent
    from src.api.models.team import TeamAnalysisResponse, CoverageResult
    from datetime import datetime, timezone

    req = UpdateMemberRequest(
        pokemon_name="garchomp",
        set_id=1,
        item="Choice Scarf",
        tera_type="dragon",
        evs={"hp": 4, "attack": 252, "defense": 0,
             "sp_attack": 0, "sp_defense": 0, "speed": 252},
        moves=["earthquake", "outrage", "stone-edge", "fire-fang"],
        nature="jolly",
        ability="rough-skin",
    )

    _sc = ScoreComponent(score=1.0, reason="test")
    _bd = ScoreBreakdown(coverage=_sc, defensive=_sc, role=_sc, speed_control=_sc, lead_pair=_sc)
    _an = TeamAnalysisResponse(
        valid=True, issues=[], roles={}, weaknesses={}, resistances={},
        coverage=CoverageResult(covered_types=[], missing_types=[]),
    )
    _now = datetime(2026, 5, 2, tzinfo=timezone.utc)

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cur.rowcount = 1
    cur.fetchone.return_value = (1, "My Team", 8.5, _now,
                                 _bd.model_dump(), _an.model_dump())
    cur.fetchall.return_value = [
        (0, "garchomp", 1, "Scarfer", "jolly", "rough-skin",
         "Choice Scarf", "dragon",
         {"hp": 4, "attack": 252, "defense": 0,
          "sp_attack": 0, "sp_defense": 0, "speed": 252},
         ["earthquake", "outrage", "stone-edge", "fire-fang"]),
    ] + [(i, f"poke{i}", i, None, None, None, None, None, None, None) for i in range(1, 6)]

    with patch("src.api.services.saved_team_service.score_team") as mock_score:
        result = update_member(conn, team_id=1, slot=0, request=req)

    mock_score.assert_not_called()
    assert isinstance(result, SavedTeamDetail)


def test_update_member_raises_on_missing_slot():
    from src.api.services.saved_team_service import update_member
    from src.api.models.saved_team import UpdateMemberRequest

    req = UpdateMemberRequest(pokemon_name="pikachu", set_id=99)

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cur.rowcount = 0

    with pytest.raises(ValueError, match="not found"):
        update_member(conn, team_id=999, slot=0, request=req)


def test_load_members_returns_item_and_tera_type():
    """_load_members maps new columns into SavedTeamMember fields."""
    from src.api.services.saved_team_service import _load_members

    cur = MagicMock()
    cur.fetchall.return_value = [
        # slot, pokemon_name, set_id, set_name, nature, ability,
        # item, tera_type, evs, moves
        (0, "garchomp", 1, "Scarfer", "jolly", "rough-skin",
         "Choice Scarf", "dragon",
         {"hp": 4, "attack": 252, "defense": 0,
          "sp_attack": 0, "sp_defense": 0, "speed": 252},
         ["earthquake", "outrage", "stone-edge", "fire-fang"]),
    ]

    members = _load_members(cur, team_id=1)

    assert len(members) == 1
    m = members[0]
    assert m.item == "Choice Scarf"
    assert m.tera_type == "dragon"
    assert m.evs["attack"] == 252
    assert m.moves == ["earthquake", "outrage", "stone-edge", "fire-fang"]
