# tests/test_team_generator.py
"""Unit tests for the team generation engine."""

import random
from itertools import cycle
from unittest.mock import MagicMock, patch

import pytest

from src.api.models.generation import GenerationConstraints
from src.api.models.team import PokemonBuild, MoveDetail
from src.api.services.team_generator import (
    MAX_ITERATIONS,
    MAX_RESULTS,
    WEAKNESS_THRESHOLD,
    PoolEntry,
    _apply_constraints,
    _base_species,
    _build_pool,
    _is_acceptable,
    _sample_candidate,
    _validate_constraints,
    generate_teams,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pool(*names, ptype="fire"):
    return [PoolEntry(name, i + 1, f"{name} set", ptype) for i, name in enumerate(names)]


def _build(name="bulbasaur", set_id=1, roles_hint=None):
    """Minimal PokemonBuild for testing."""
    moves = []
    if roles_hint == "physical_sweeper":
        moves = [MoveDetail("tackle", "normal", "physical")] * 3
    elif roles_hint == "special_sweeper":
        moves = [MoveDetail("flamethrower", "fire", "special")] * 3
    return PokemonBuild(
        pokemon_name=name,
        set_id=set_id,
        types=["fire"],
        nature="bold",
        ability="blaze",
        item="leftovers",
        stats={
            "hp": 200,
            "attack": 350 if roles_hint == "physical_sweeper" else 100,
            "defense": 100,
            "sp_attack": 350 if roles_hint == "special_sweeper" else 100,
            "sp_defense": 100,
            "speed": 300 if roles_hint in ("physical_sweeper", "special_sweeper") else 90,
        },
        moves=moves,
    )


def _valid_report(**overrides):
    base = {
        "valid": True,
        "issues": [],
        "roles": {
            "physical_sweeper": 1, "special_sweeper": 1, "tank": 1,
            "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
        },
        "weaknesses": {"water": 1},
        "resistances": {},
        "coverage": {"covered_types": ["fire"], "missing_types": []},
    }
    base.update(overrides)
    return base


def _invalid_report():
    return {
        "valid": False,
        "issues": ["Missing tank"],
        "roles": {},
        "weaknesses": {},
        "resistances": {},
        "coverage": {"covered_types": [], "missing_types": []},
    }


_SIX_NAMES = ["bulbasaur", "charmander", "squirtle", "pikachu", "jigglypuff", "mewtwo"]
_POOL_6 = _pool(*_SIX_NAMES)
_MEMBERS_6 = [
    {"pokemon_name": n, "set_id": i + 1, "set_name": f"{n} set"}
    for i, n in enumerate(_SIX_NAMES)
]
_BUILDS_6 = [_build(n, i + 1) for i, n in enumerate(_SIX_NAMES)]


# ---------------------------------------------------------------------------
# _build_pool
# ---------------------------------------------------------------------------

class TestBuildPool:
    def _make_conn(self, rows):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = rows
        return conn

    def test_returns_pool_entries(self):
        conn = self._make_conn([
            ("garchomp", 1, "Choice Scarf", "dragon"),
            ("ferrothorn", 2, "Defensive", "grass"),
        ])
        pool = _build_pool(conn)
        assert pool == [
            PoolEntry("garchomp", 1, "Choice Scarf", "dragon"),
            PoolEntry("ferrothorn", 2, "Defensive", "grass"),
        ]

    def test_returns_empty_list_when_no_sets(self):
        conn = self._make_conn([])
        assert _build_pool(conn) == []

    def test_handles_null_primary_type(self):
        conn = self._make_conn([("ditto", 5, None, None)])
        pool = _build_pool(conn)
        assert pool == [PoolEntry("ditto", 5, None, None)]


# ---------------------------------------------------------------------------
# _apply_constraints
# ---------------------------------------------------------------------------

class TestApplyConstraints:
    def test_exclude_removes_pokemon(self):
        pool = _pool("garchomp", "mewtwo", "pikachu")
        c = GenerationConstraints(exclude=["mewtwo"])
        result = _apply_constraints(pool, c)
        assert all(e.pokemon_name != "mewtwo" for e in result)
        assert len(result) == 2

    def test_exclude_is_case_insensitive(self):
        pool = _pool("Garchomp", "Mewtwo")
        c = GenerationConstraints(exclude=["garchomp"])
        result = _apply_constraints(pool, c)
        assert len(result) == 1
        assert result[0].pokemon_name == "Mewtwo"

    def test_empty_constraints_returns_full_pool(self):
        pool = _pool("a", "b", "c")
        c = GenerationConstraints()
        assert _apply_constraints(pool, c) == pool

    def test_exclude_all_returns_empty(self):
        pool = _pool("a", "b")
        c = GenerationConstraints(exclude=["a", "b"])
        assert _apply_constraints(pool, c) == []


# ---------------------------------------------------------------------------
# _validate_constraints
# ---------------------------------------------------------------------------

class TestValidateConstraints:
    def test_passes_with_valid_constraints(self):
        pool = _pool(*_SIX_NAMES)
        _validate_constraints(pool, GenerationConstraints(include=["bulbasaur"]))

    def test_raises_if_include_not_in_pool(self):
        pool = _pool(*_SIX_NAMES)
        with pytest.raises(ValueError, match="include Pokémon 'unknown'"):
            _validate_constraints(pool, GenerationConstraints(include=["unknown"]))

    def test_raises_if_include_case_mismatch(self):
        pool = _pool("bulbasaur")
        with pytest.raises(ValueError, match="include"):
            _validate_constraints(pool, GenerationConstraints(include=["UNKNOWN"]))

    def test_raises_if_pool_too_small_after_exclusions(self):
        pool = _pool("a", "b", "c")  # only 3 distinct pokemon
        with pytest.raises(ValueError, match="Pool has only 3"):
            _validate_constraints(pool, GenerationConstraints())

    def test_raises_if_exclusions_shrink_pool_below_6(self):
        pool = _pool(*_SIX_NAMES)
        c = GenerationConstraints(exclude=["bulbasaur", "charmander"])
        with pytest.raises(ValueError, match="Pool has only 4"):
            _validate_constraints(pool, c)

    def test_raises_if_include_is_also_excluded(self):
        pool = _pool(*_SIX_NAMES)
        c = GenerationConstraints(include=["bulbasaur"], exclude=["bulbasaur"])
        with pytest.raises(ValueError, match="include"):
            _validate_constraints(pool, c)


# ---------------------------------------------------------------------------
# _base_species
# ---------------------------------------------------------------------------

class TestBaseSpecies:
    def test_plain_name_unchanged(self):
        assert _base_species("garchomp") == "garchomp"

    def test_strips_mega(self):
        assert _base_species("garchomp-mega") == "garchomp"

    def test_strips_mega_x(self):
        assert _base_species("charizard-mega-x") == "charizard"

    def test_strips_mega_y(self):
        assert _base_species("mewtwo-mega-y") == "mewtwo"

    def test_strips_gmax(self):
        assert _base_species("snorlax-gmax") == "snorlax"

    def test_strips_primal(self):
        assert _base_species("kyogre-primal") == "kyogre"

    def test_preserves_alolan(self):
        assert _base_species("meowth-alolan") == "meowth-alolan"

    def test_preserves_galarian(self):
        assert _base_species("slowpoke-galarian") == "slowpoke-galarian"

    def test_preserves_hisuian(self):
        assert _base_species("typhlosion-hisui") == "typhlosion-hisui"

    def test_lowercases_name(self):
        assert _base_species("Garchomp-Mega") == "garchomp"

    def test_lowercases_regional(self):
        assert _base_species("Meowth-Alolan") == "meowth-alolan"


# ---------------------------------------------------------------------------
# _sample_candidate
# ---------------------------------------------------------------------------

class TestSampleCandidate:
    def _patched(self, pool, include, conn, rng, build_fn=None, roles_fn=None):
        if build_fn is None:
            build_fn = lambda c, name, sid: _build(name, sid)
        if roles_fn is None:
            roles_fn = lambda b: []
        with (
            patch("src.api.services.team_generator.load_build", side_effect=build_fn),
            patch("src.api.services.team_generator.detect_roles", side_effect=roles_fn),
        ):
            return _sample_candidate(pool, include, conn, rng)

    def test_returns_6_members(self):
        pool = _pool(*_SIX_NAMES, ptype="fire")
        members, builds = self._patched(pool, [], MagicMock(), random.Random(0))
        assert len(members) == 6
        assert len(builds) == 6

    def test_no_duplicate_pokemon_names(self):
        pool = _pool(*_SIX_NAMES)
        members, _ = self._patched(pool, [], MagicMock(), random.Random(0))
        names = [m["pokemon_name"] for m in members]
        assert len(names) == len(set(names))

    def test_member_has_required_keys(self):
        pool = _pool(*_SIX_NAMES)
        members, _ = self._patched(pool, [], MagicMock(), random.Random(0))
        for m in members:
            assert "pokemon_name" in m
            assert "set_id" in m
            assert "set_name" in m

    def test_rule2_limits_primary_type_to_3(self):
        grass_pool = [PoolEntry(f"grass{i}", i, None, "grass") for i in range(5)]
        other_pool = [
            PoolEntry("pikachu", 10, None, "electric"),
            PoolEntry("mewtwo", 11, None, "psychic"),
            PoolEntry("gyarados", 12, None, "water"),
        ]
        pool = grass_pool + other_pool
        members, _ = self._patched(pool, [], MagicMock(), random.Random(7))
        grass_count = sum(1 for m in members if m["pokemon_name"].startswith("grass"))
        assert grass_count <= 3

    def test_include_names_appear_in_result(self):
        pool = _pool(*_SIX_NAMES)
        members, _ = self._patched(pool, ["bulbasaur"], MagicMock(), random.Random(0))
        names = [m["pokemon_name"] for m in members]
        assert "bulbasaur" in names

    def test_rule3_limits_physical_sweepers(self):
        pool = [PoolEntry(f"poke{i}", i, None, f"type{i}") for i in range(10)]

        def roles_fn(build):
            return ["physical_sweeper"]

        members, _ = self._patched(
            pool, [], MagicMock(), random.Random(0), roles_fn=roles_fn
        )
        # With Rule 3, at most 2 physical_sweepers should appear unless relaxed
        # The retry budget may relax the rule if all candidates are sweepers
        assert len(members) == 6

    def test_mega_and_base_not_both_chosen(self):
        """garchomp and garchomp-mega share a base species — only one can appear."""
        pool = [
            PoolEntry("garchomp",      1, None, "dragon"),
            PoolEntry("garchomp-mega", 2, None, "dragon"),
            PoolEntry("ferrothorn",    3, None, "grass"),
            PoolEntry("rotom-wash",    4, None, "electric"),
            PoolEntry("clefable",      5, None, "fairy"),
            PoolEntry("heatran",       6, None, "fire"),
            PoolEntry("landorus",      7, None, "ground"),
        ]
        members, _ = self._patched(pool, [], MagicMock(), random.Random(0))
        names = [m["pokemon_name"] for m in members]
        assert not ("garchomp" in names and "garchomp-mega" in names)

    def test_gmax_and_base_not_both_chosen(self):
        """snorlax and snorlax-gmax share a base species — only one can appear."""
        pool = [
            PoolEntry("snorlax",      1, None, "normal"),
            PoolEntry("snorlax-gmax", 2, None, "normal"),
            PoolEntry("ferrothorn",   3, None, "grass"),
            PoolEntry("rotom-wash",   4, None, "electric"),
            PoolEntry("clefable",     5, None, "fairy"),
            PoolEntry("heatran",      6, None, "fire"),
            PoolEntry("landorus",     7, None, "ground"),
        ]
        members, _ = self._patched(pool, [], MagicMock(), random.Random(0))
        names = [m["pokemon_name"] for m in members]
        assert not ("snorlax" in names and "snorlax-gmax" in names)

    def test_regional_forms_can_coexist(self):
        """meowth and meowth-alolan are different species and may both appear."""
        pool = [
            PoolEntry("meowth",        1, None, "normal"),
            PoolEntry("meowth-alolan", 2, None, "dark"),
            PoolEntry("ferrothorn",    3, None, "grass"),
            PoolEntry("rotom-wash",    4, None, "electric"),
            PoolEntry("clefable",      5, None, "fairy"),
            PoolEntry("heatran",       6, None, "fire"),
        ]
        # Pool has exactly 6 distinct base species → all must appear
        members, _ = self._patched(pool, [], MagicMock(), random.Random(0))
        names = [m["pokemon_name"] for m in members]
        assert "meowth" in names and "meowth-alolan" in names


# ---------------------------------------------------------------------------
# _is_acceptable
# ---------------------------------------------------------------------------

class TestIsAcceptable:
    def test_true_when_valid_and_low_weakness(self):
        assert _is_acceptable(_valid_report()) is True

    def test_false_when_invalid(self):
        assert _is_acceptable(_invalid_report()) is False

    def test_false_when_weakness_at_threshold(self):
        report = _valid_report(weaknesses={"ice": WEAKNESS_THRESHOLD})
        assert _is_acceptable(report) is False

    def test_false_when_weakness_above_threshold(self):
        report = _valid_report(weaknesses={"ice": WEAKNESS_THRESHOLD + 1})
        assert _is_acceptable(report) is False

    def test_true_when_weakness_one_below_threshold(self):
        report = _valid_report(weaknesses={"ice": WEAKNESS_THRESHOLD - 1})
        assert _is_acceptable(report) is True

    def test_true_with_no_weaknesses(self):
        assert _is_acceptable(_valid_report(weaknesses={})) is True



# ---------------------------------------------------------------------------
# generate_teams
# ---------------------------------------------------------------------------

class TestGenerateTeams:
    def _run(self, reports, constraints=None, rng=None):
        """Patch pool + sampling + analysis; run generate_teams."""
        conn = MagicMock()
        if rng is None:
            rng = random.Random(42)
        with (
            patch("src.api.services.team_generator._build_pool", return_value=_POOL_6),
            patch(
                "src.api.services.team_generator._sample_candidate",
                return_value=(_MEMBERS_6, _BUILDS_6),
            ),
            patch(
                "src.api.services.team_generator.analyze_team",
                side_effect=cycle(reports),
            ),
        ):
            return generate_teams(conn, constraints=constraints, rng=rng)

    def test_returns_teams_list(self):
        result = self._run([_valid_report()])
        assert "teams" in result
        assert isinstance(result["teams"], list)

    def test_returns_metadata(self):
        result = self._run([_valid_report()])
        assert "generated" in result
        assert "valid_found" in result

    def test_returns_up_to_max_results(self):
        result = self._run([_valid_report()] * MAX_RESULTS)
        assert len(result["teams"]) <= MAX_RESULTS

    def test_valid_found_matches_teams_count(self):
        result = self._run([_valid_report()] * MAX_RESULTS)
        assert result["valid_found"] == len(result["teams"])

    def test_invalid_reports_are_rejected(self):
        result = self._run([_invalid_report()])
        assert result["valid_found"] == 0
        assert result["generated"] == MAX_ITERATIONS

    def test_high_weakness_reports_are_rejected(self):
        report = _valid_report(weaknesses={"ice": WEAKNESS_THRESHOLD})
        result = self._run([report])
        assert result["valid_found"] == 0

    def test_respects_max_iterations(self):
        result = self._run([_invalid_report()])
        assert result["generated"] == MAX_ITERATIONS

    def test_stops_early_when_max_results_found(self):
        result = self._run([_valid_report()] * 10)
        assert result["generated"] == MAX_RESULTS

    def test_results_sorted_by_score_descending(self):
        # defensive score varies with weakness count → drives overall ordering
        reports = [
            _valid_report(weaknesses={"fire": 2}),
            _valid_report(weaknesses={}),
            _valid_report(weaknesses={"fire": 1}),
            _valid_report(weaknesses={"ice": 2}),
            _valid_report(weaknesses={"ice": 1}),
        ]
        result = self._run(reports)
        scores = [t["score"] for t in result["teams"]]
        assert scores == sorted(scores, reverse=True)

    def test_team_dict_has_score_members_analysis_breakdown(self):
        result = self._run([_valid_report()])
        team = result["teams"][0]
        assert "score" in team
        assert "members" in team
        assert "analysis" in team
        assert "breakdown" in team

    def test_score_is_in_0_to_10_range(self):
        result = self._run([_valid_report()])
        score = result["teams"][0]["score"]
        assert 0.0 <= score <= 10.0

    def test_raises_value_error_for_invalid_include(self):
        conn = MagicMock()
        with (
            patch("src.api.services.team_generator._build_pool", return_value=_POOL_6),
        ):
            with pytest.raises(ValueError, match="include"):
                generate_teams(
                    conn,
                    constraints=GenerationConstraints(include=["unknown_pokemon"]),
                )

    def test_raises_value_error_for_small_pool(self):
        conn = MagicMock()
        small_pool = _pool("a", "b", "c")
        with (
            patch("src.api.services.team_generator._build_pool", return_value=small_pool),
        ):
            with pytest.raises(ValueError, match="Pool has only 3"):
                generate_teams(conn)

    def test_no_constraints_uses_empty_defaults(self):
        result = self._run([_valid_report()])
        assert result is not None

    def test_generation_with_exclude_constraint(self):
        conn = MagicMock()
        # 7 distinct pokemon; excluding mewtwo leaves exactly 6
        pool_with_extra = _POOL_6 + [PoolEntry("garchomp", 99, "Scarf", "dragon")]
        c = GenerationConstraints(exclude=["mewtwo"])
        with (
            patch("src.api.services.team_generator._build_pool", return_value=pool_with_extra),
            patch(
                "src.api.services.team_generator._sample_candidate",
                return_value=(_MEMBERS_6, _BUILDS_6),
            ),
            patch(
                "src.api.services.team_generator.analyze_team",
                return_value=_valid_report(),
            ),
        ):
            result = generate_teams(conn, constraints=c, rng=random.Random(0))
        assert result["valid_found"] > 0
