# tests/test_team_optimizer.py
"""Unit tests for the GA team optimizer."""

import random
from unittest.mock import MagicMock, patch

import pytest

from src.api.services.team_optimizer import (
    _cache_key,
    _crossover,
    _evaluate,
    _mutate,
    _repair,
    _seed_population,
    _tournament_select,
    optimize_team,
    CHILDREN_PER_GENERATION_RATIO,
    CROSSOVER_RATE,
    MUTATION_RATE,
    MUTATION_TYPE_SPLIT,
    POPULATION_SIZE,
    TEAM_SIZE,
    TOURNAMENT_K,
)
from src.api.services.team_generator import PoolEntry
from src.api.models.generation import GenerationConstraints


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chromosome(names=("a", "b", "c", "d", "e", "f"), base_sid=1):
    return [(name, base_sid + i) for i, name in enumerate(names)]


def _pool(*names):
    return [PoolEntry(name, i + 1, None, "fire") for i, name in enumerate(names)]


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_returns_frozenset(self):
        chrom = _make_chromosome()
        assert isinstance(_cache_key(chrom), frozenset)

    def test_order_independent(self):
        chrom1 = [("a", 1), ("b", 2), ("c", 3)]
        chrom2 = [("c", 3), ("a", 1), ("b", 2)]
        assert _cache_key(chrom1) == _cache_key(chrom2)

    def test_different_chromosomes_differ(self):
        chrom1 = [("a", 1), ("b", 2), ("c", 3)]
        chrom2 = [("a", 1), ("b", 2), ("d", 4)]
        assert _cache_key(chrom1) != _cache_key(chrom2)


# ---------------------------------------------------------------------------
# _seed_population
# ---------------------------------------------------------------------------

class TestSeedPopulation:
    def _pool_6(self):
        return [PoolEntry(f"poke{i}", i, None, "fire") for i in range(1, 25)]

    def test_returns_list_of_chromosomes(self):
        pool = self._pool_6()
        rng = random.Random(42)
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team") as mock_at,
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
        ):
            members = [
                {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
                for i in range(1, 7)
            ]
            mock_sc.return_value = (members, [MagicMock()] * 6)
            mock_at.return_value = {"valid": True, "weaknesses": {}}
            result = _seed_population(pool, mock_conn, rng, 3)
        assert isinstance(result, list)
        assert all(isinstance(c, list) for c in result)

    def test_each_chromosome_has_6_members(self):
        pool = self._pool_6()
        rng = random.Random(42)
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team") as mock_at,
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
        ):
            members = [
                {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
                for i in range(1, 7)
            ]
            mock_sc.return_value = (members, [MagicMock()] * 6)
            mock_at.return_value = {"valid": True, "weaknesses": {}}
            result = _seed_population(pool, mock_conn, rng, 3)
        assert all(len(c) == 6 for c in result)

    def test_respects_size_limit(self):
        pool = self._pool_6()
        rng = random.Random(42)
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team") as mock_at,
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
        ):
            members = [
                {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
                for i in range(1, 7)
            ]
            mock_sc.return_value = (members, [MagicMock()] * 6)
            mock_at.return_value = {"valid": True, "weaknesses": {}}
            result = _seed_population(pool, mock_conn, rng, 5)
        assert len(result) <= 5

    def test_partial_population_when_acceptance_low(self):
        pool = self._pool_6()
        rng = random.Random(42)
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team") as mock_at,
            patch("src.api.services.team_optimizer._is_acceptable", return_value=False),
        ):
            members = [
                {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
                for i in range(1, 7)
            ]
            mock_sc.return_value = (members, [MagicMock()] * 6)
            mock_at.return_value = {"valid": False, "weaknesses": {}}
            result = _seed_population(pool, mock_conn, rng, 5)
        assert result == []


# ---------------------------------------------------------------------------
# _evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    def _make_chrom(self):
        return [("bulbasaur", 1), ("charmander", 2), ("squirtle", 3),
                ("pikachu", 4), ("gengar", 5), ("snorlax", 6)]

    def test_returns_float(self):
        chrom = self._make_chrom()
        cache: dict = {}
        eval_count = [0]
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.analyze_team", return_value={}),
            patch("src.api.services.team_optimizer.score_team", return_value={"score": 7.5}),
        ):
            result = _evaluate(chrom, mock_conn, cache, eval_count)
        assert isinstance(result, float)
        assert result == 7.5

    def test_increments_eval_count_on_cache_miss(self):
        chrom = self._make_chrom()
        cache: dict = {}
        eval_count = [0]
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.analyze_team", return_value={}),
            patch("src.api.services.team_optimizer.score_team", return_value={"score": 7.5}),
        ):
            _evaluate(chrom, mock_conn, cache, eval_count)
        assert eval_count[0] == 1

    def test_no_increment_on_cache_hit(self):
        chrom = self._make_chrom()
        key = _cache_key(chrom)
        cache = {key: 8.0}
        eval_count = [0]
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer.load_build") as mock_lb,
        ):
            result = _evaluate(chrom, mock_conn, cache, eval_count)
        assert eval_count[0] == 0
        mock_lb.assert_not_called()

    def test_cache_hit_returns_cached_value(self):
        chrom = self._make_chrom()
        key = _cache_key(chrom)
        cache = {key: 9.5}
        eval_count = [0]
        mock_conn = MagicMock()
        with patch("src.api.services.team_optimizer.load_build") as mock_lb:
            result = _evaluate(chrom, mock_conn, cache, eval_count)
            mock_lb.assert_not_called()
        assert result == 9.5

    def test_result_stored_in_cache(self):
        chrom = self._make_chrom()
        cache: dict = {}
        eval_count = [0]
        mock_conn = MagicMock()
        with (
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.analyze_team", return_value={}),
            patch("src.api.services.team_optimizer.score_team", return_value={"score": 7.5}),
        ):
            _evaluate(chrom, mock_conn, cache, eval_count)
        assert _cache_key(chrom) in cache


# ---------------------------------------------------------------------------
# _tournament_select
# ---------------------------------------------------------------------------

class TestTournamentSelect:
    def _population(self):
        return [
            [("a", 1), ("b", 2), ("c", 3), ("d", 4), ("e", 5), ("f", 6)],
            [("g", 7), ("h", 8), ("i", 9), ("j", 10), ("k", 11), ("l", 12)],
            [("m", 13), ("n", 14), ("o", 15), ("p", 16), ("q", 17), ("r", 18)],
            [("s", 19), ("t", 20), ("u", 21), ("v", 22), ("w", 23), ("x", 24)],
        ]

    def _scores(self, population, values):
        return {_cache_key(ind): v for ind, v in zip(population, values)}

    def test_returns_a_population_member(self):
        pop = self._population()
        scores = self._scores(pop, [5.0, 7.0, 6.0, 8.0])
        rng = random.Random(42)
        result = _tournament_select(pop, scores, 3, rng)
        # Result must be one of the population members
        assert any(result == member for member in pop)

    def test_returns_best_of_tournament(self):
        pop = self._population()
        # Assign clear winner at index 2 (score 9.9)
        scores = self._scores(pop, [3.0, 3.0, 9.9, 3.0])
        rng = random.Random(42)
        # With k=len(pop), tournament sees all — must return the highest scorer
        result = _tournament_select(pop, scores, len(pop), rng)
        assert result == pop[2]

    def test_returns_highest_score_in_tournament(self):
        pop = self._population()
        scores = self._scores(pop, [5.0, 7.0, 6.0, 8.0])
        rng = random.Random(42)
        result = _tournament_select(pop, scores, len(pop), rng)
        assert result == pop[3]

    def test_handles_small_population(self):
        pop = self._population()[:2]
        scores = self._scores(pop, [5.0, 9.0])
        rng = random.Random(42)
        result = _tournament_select(pop, scores, 10, rng)
        assert result in pop


# ---------------------------------------------------------------------------
# _crossover
# ---------------------------------------------------------------------------

class TestCrossover:
    def _parent(self, prefix):
        return [(f"{prefix}{i}", i) for i in range(1, 7)]

    def test_child_has_6_members(self):
        rng = random.Random(42)
        child = _crossover(self._parent("a"), self._parent("b"), rng)
        assert len(child) == 6

    def test_child_contains_elements_from_both_parents(self):
        rng = random.Random(0)
        pa = self._parent("a")
        pb = self._parent("b")
        child = _crossover(pa, pb, rng)
        from_a = [e for e in child if e in pa]
        from_b = [e for e in child if e in pb]
        assert len(from_a) > 0
        assert len(from_b) > 0

    def test_first_slot_always_from_parent_a(self):
        # cut is always >= 1, so child[0] must come from parent_a
        pa = [("a1", 1), ("a2", 2), ("a3", 3), ("a4", 4), ("a5", 5), ("a6", 6)]
        pb = [("b1", 7), ("b2", 8), ("b3", 9), ("b4", 10), ("b5", 11), ("b6", 12)]
        for seed in range(20):
            child = _crossover(pa, pb, random.Random(seed))
            assert child[0] == pa[0]

    def test_last_slot_always_from_parent_b(self):
        # cut is always <= 5, so child[5] must come from parent_b
        pa = [("a1", 1), ("a2", 2), ("a3", 3), ("a4", 4), ("a5", 5), ("a6", 6)]
        pb = [("b1", 7), ("b2", 8), ("b3", 9), ("b4", 10), ("b5", 11), ("b6", 12)]
        for seed in range(20):
            child = _crossover(pa, pb, random.Random(seed))
            assert child[5] == pb[5]


# ---------------------------------------------------------------------------
# _repair
# ---------------------------------------------------------------------------

class TestRepair:
    def _pool(self):
        names = ["pikachu", "bulbasaur", "charmander", "squirtle",
                 "gengar", "snorlax", "mewtwo", "eevee"]
        return [PoolEntry(n, i + 1, None, "normal") for i, n in enumerate(names)]

    def test_no_duplicates_unchanged(self):
        pool = self._pool()
        child = [("pikachu", 1), ("bulbasaur", 2), ("charmander", 3),
                 ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]
        rng = random.Random(42)
        result = _repair(child, pool, rng)
        assert result == child

    def test_duplicate_base_species_replaced(self):
        pool = self._pool()
        child = [("pikachu", 1), ("bulbasaur", 2), ("pikachu", 1),
                 ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]
        rng = random.Random(42)
        result = _repair(child, pool, rng)
        names = [name for name, _ in result]
        assert len(set(names)) == len(names)

    def test_result_length_unchanged(self):
        pool = self._pool()
        child = [("pikachu", 1), ("pikachu", 1), ("pikachu", 1),
                 ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]
        rng = random.Random(42)
        result = _repair(child, pool, rng)
        assert len(result) == 6

    def test_first_occurrence_kept(self):
        pool = self._pool()
        child = [("pikachu", 1), ("bulbasaur", 2), ("pikachu", 1),
                 ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]
        rng = random.Random(42)
        result = _repair(child, pool, rng)
        assert result[0] == ("pikachu", 1)

    def test_does_not_mutate_original(self):
        pool = self._pool()
        child = [("pikachu", 1), ("bulbasaur", 2), ("pikachu", 1),
                 ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]
        original = list(child)
        rng = random.Random(42)
        _repair(child, pool, rng)
        assert child == original

    def test_exhaustion_keeps_duplicate(self):
        # Pool only has "pikachu" entries — repair budget will be exhausted
        # and the duplicate will survive
        pool = [PoolEntry("pikachu", 1, None, "normal"), PoolEntry("pikachu", 2, None, "normal")]
        child = [("pikachu", 1), ("bulbasaur", 2), ("pikachu", 1),
                 ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]
        rng = random.Random(42)
        result = _repair(child, pool, rng)
        # Length must still be 6 even if duplicate couldn't be fixed
        assert len(result) == 6


# ---------------------------------------------------------------------------
# _mutate
# ---------------------------------------------------------------------------

class TestMutate:
    def _chromosome(self):
        return [("pikachu", 1), ("bulbasaur", 2), ("charmander", 3),
                ("squirtle", 4), ("gengar", 5), ("snorlax", 6)]

    def _pool(self):
        names = ["pikachu", "bulbasaur", "charmander", "squirtle",
                 "gengar", "snorlax", "mewtwo", "eevee", "jolteon",
                 "vaporeon", "flareon"]
        entries = [PoolEntry(n, i + 1, None, "normal") for i, n in enumerate(names)]
        # Second set for pikachu — enables type-2 (swap set) mutation
        entries.append(PoolEntry("pikachu", 99, None, "electric"))
        return entries

    def test_returns_chromosome_of_length_6(self):
        rng = random.Random(42)
        result = _mutate(self._chromosome(), self._pool(), rng)
        assert len(result) == 6

    def test_result_has_no_duplicate_base_species(self):
        rng = random.Random(42)
        for seed in range(30):
            result = _mutate(self._chromosome(), self._pool(), random.Random(seed))
            bases = [b for b, _ in result]
            assert len(set(bases)) == len(bases), f"Duplicate base species with seed={seed}"

    def test_type2_swap_set_keeps_pokemon_name(self):
        pool = self._pool()
        # Find a seed that produces type-2 mutation on pikachu slot (has alt set 99)
        found_swap = False
        for seed in range(100):
            r = random.Random(seed)
            original = self._chromosome()
            result = _mutate(list(original), pool, r)
            for (on, os_), (rn, rs_) in zip(original, result):
                if on == rn and os_ != rs_:
                    found_swap = True
                    assert on == rn  # name preserved
                    break
            if found_swap:
                break
        assert found_swap, "Expected at least one type-2 (swap set) mutation in 100 seeds"

    def test_does_not_mutate_original(self):
        original = self._chromosome()
        original_copy = list(original)
        rng = random.Random(42)
        _mutate(original, self._pool(), rng)
        assert original == original_copy

    def test_type1_changes_a_slot(self):
        # Run many seeds; at least one should produce a type-1 mutation that changes the team
        found_change = False
        for seed in range(50):
            original = self._chromosome()
            result = _mutate(list(original), self._pool(), random.Random(seed))
            if result != original:
                found_change = True
                break
        assert found_change, "Expected at least one mutation to change the team in 50 seeds"

    def test_type1_empty_filtered_pool_falls_back(self):
        # Pool only contains the same species as the chromosome — filtered pool will be empty
        # Fallback to full pool should prevent an error
        pool = [PoolEntry("pikachu", i, None, "normal") for i in range(1, 10)]
        child = [("pikachu", 1), ("pikachu", 2), ("pikachu", 3),
                 ("pikachu", 4), ("pikachu", 5), ("pikachu", 6)]
        rng = random.Random(42)
        # Should not raise, even though filtered pool is empty
        result = _mutate(child, pool, rng)
        assert len(result) == 6


# ---------------------------------------------------------------------------
# optimize_team
# ---------------------------------------------------------------------------

class TestOptimizeTeam:
    def _mock_analysis(self):
        return {
            "valid": True,
            "issues": [],
            "roles": {
                "physical_sweeper": 1, "special_sweeper": 1, "tank": 1,
                "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
            },
            "weaknesses": {"water": 1},
            "resistances": {},
            "coverage": {
                "covered_types": ["fire", "water", "grass"],
                "missing_types": [],
            },
        }

    def _mock_scoring(self):
        return {
            "score": 7.0,
            "breakdown": {
                "coverage":  {"score": 0.5, "reason": "ok"},
                "defensive": {"score": 0.8, "reason": "ok"},
                "role":      {"score": 1.0, "reason": "ok"},
                "speed":     {"score": 1.0, "reason": "ok"},
            },
        }

    def _members(self, n=6):
        return [
            {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
            for i in range(1, n + 1)
        ]

    def _run_optimize(self, generations=2, population_size=5):
        mock_conn = MagicMock()
        pool = [PoolEntry(f"poke{i}", i, None, "fire") for i in range(1, 25)]
        rng = random.Random(42)
        with (
            patch("src.api.services.team_optimizer._build_pool", return_value=pool),
            patch("src.api.services.team_optimizer._validate_constraints"),
            patch("src.api.services.team_optimizer._apply_constraints", return_value=pool),
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team", return_value=self._mock_analysis()),
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.score_team", return_value=self._mock_scoring()),
        ):
            mock_sc.return_value = (self._members(), [MagicMock()] * 6)
            return optimize_team(
                mock_conn,
                generations=generations,
                population_size=population_size,
                rng=rng,
            )

    def test_returns_dict_with_required_keys(self):
        result = self._run_optimize()
        assert set(result.keys()) >= {"best_teams", "generations_run", "initial_population", "evaluations"}

    def test_generations_run_matches_param(self):
        result = self._run_optimize(generations=3)
        assert result["generations_run"] == 3

    def test_evaluations_is_int(self):
        result = self._run_optimize()
        assert isinstance(result["evaluations"], int)

    def test_best_teams_have_required_keys(self):
        result = self._run_optimize()
        for team in result["best_teams"]:
            assert "score" in team
            assert "breakdown" in team
            assert "members" in team
            assert "analysis" in team

    def test_initial_population_is_int(self):
        result = self._run_optimize()
        assert isinstance(result["initial_population"], int)

    def test_population_size_capped_at_100(self):
        mock_conn = MagicMock()
        pool = [PoolEntry(f"poke{i}", i, None, "fire") for i in range(1, 25)]
        rng = random.Random(42)
        members = [
            {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
            for i in range(1, 7)
        ]
        with (
            patch("src.api.services.team_optimizer._build_pool", return_value=pool),
            patch("src.api.services.team_optimizer._validate_constraints"),
            patch("src.api.services.team_optimizer._apply_constraints", return_value=pool),
            patch("src.api.services.team_optimizer._sample_candidate", return_value=(members, [MagicMock()] * 6)),
            patch("src.api.services.team_optimizer.analyze_team", return_value={
                "valid": True, "weaknesses": {}, "issues": [], "roles": {
                    "physical_sweeper": 1, "special_sweeper": 1, "tank": 1,
                    "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
                }, "resistances": {}, "coverage": {"covered_types": [], "missing_types": []},
            }),
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.score_team", return_value={
                "score": 5.0,
                "breakdown": {
                    "coverage": {"score": 0.5, "reason": "ok"},
                    "defensive": {"score": 0.5, "reason": "ok"},
                    "role": {"score": 0.5, "reason": "ok"},
                    "speed": {"score": 0.5, "reason": "ok"},
                },
            }),
        ):
            result = optimize_team(mock_conn, population_size=200, generations=2, rng=rng)
        assert result["initial_population"] <= 100

    def test_generations_capped_at_50(self):
        result = self._run_optimize(generations=100)
        assert result["generations_run"] <= 50

    def test_small_population_size_does_not_crash(self):
        # population_size=1 triggers the max(1, ...) guard in children_per_gen
        mock_conn = MagicMock()
        pool = [PoolEntry(f"poke{i}", i, None, "fire") for i in range(1, 25)]
        rng = random.Random(42)
        members = [
            {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
            for i in range(1, 7)
        ]
        with (
            patch("src.api.services.team_optimizer._build_pool", return_value=pool),
            patch("src.api.services.team_optimizer._validate_constraints"),
            patch("src.api.services.team_optimizer._apply_constraints", return_value=pool),
            patch("src.api.services.team_optimizer._sample_candidate", return_value=(members, [MagicMock()] * 6)),
            patch("src.api.services.team_optimizer.analyze_team", return_value={
                "valid": True, "weaknesses": {}, "issues": [], "roles": {
                    "physical_sweeper": 1, "special_sweeper": 1, "tank": 1,
                    "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
                }, "resistances": {}, "coverage": {"covered_types": [], "missing_types": []},
            }),
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.score_team", return_value={
                "score": 5.0,
                "breakdown": {
                    "coverage": {"score": 0.5, "reason": "ok"},
                    "defensive": {"score": 0.5, "reason": "ok"},
                    "role": {"score": 0.5, "reason": "ok"},
                    "speed": {"score": 0.5, "reason": "ok"},
                },
            }),
        ):
            result = optimize_team(mock_conn, population_size=1, generations=2, rng=rng)
        assert isinstance(result, dict)
        assert "best_teams" in result


# ---------------------------------------------------------------------------
# optimize_team regulation integration
# ---------------------------------------------------------------------------

class TestOptimizeTeamWithRegulation:
    def _pool(self, n=20):
        return [PoolEntry(f"poke{i}", i, None, "fire") for i in range(1, n + 1)]

    def _members(self):
        return [
            {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
            for i in range(1, 7)
        ]

    def _mock_analysis(self):
        return {
            "valid": True, "issues": [], "roles": {}, "weaknesses": {},
            "resistances": {}, "coverage": {"covered_types": [], "missing_types": []},
        }

    def _mock_scoring(self):
        return {
            "score": 7.0,
            "breakdown": {
                "coverage": {"score": 1.0, "reason": "ok"},
                "defensive": {"score": 1.0, "reason": "ok"},
                "role": {"score": 1.0, "reason": "ok"},
                "speed": {"score": 1.0, "reason": "ok"},
            },
        }

    def test_regulation_id_calls_get_regulation_info(self):
        allowed_names = {f"poke{i}" for i in range(1, 21)}
        with (
            patch("src.api.services.team_optimizer.regulation_service.get_regulation_info",
                  return_value=("Reg E", allowed_names)) as mock_info,
            patch("src.api.services.team_optimizer._build_pool",
                  return_value=self._pool()),
            patch("src.api.services.team_optimizer._validate_constraints"),
            patch("src.api.services.team_optimizer._apply_constraints",
                  return_value=self._pool()),
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team",
                  return_value=self._mock_analysis()),
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.score_team",
                  return_value=self._mock_scoring()),
        ):
            mock_sc.return_value = (self._members(), [MagicMock()] * 6)
            conn = MagicMock()
            constraints = GenerationConstraints(regulation_id=1)
            optimize_team(conn, constraints=constraints, population_size=3, generations=1,
                          rng=random.Random(42))
            mock_info.assert_called_once_with(conn, 1)

    def test_include_banned_by_regulation_raises(self):
        allowed_names = {"bulbasaur", "charmander"}
        with (
            patch("src.api.services.team_optimizer._build_pool",
                  return_value=[PoolEntry("bulbasaur", 1, None, "grass")]),
            patch("src.api.services.team_optimizer.regulation_service.get_regulation_info",
                  return_value=("Reg E", allowed_names)),
        ):
            conn = MagicMock()
            constraints = GenerationConstraints(include=["mewtwo"], regulation_id=1)
            with pytest.raises(ValueError, match="not permitted under the selected regulation"):
                optimize_team(conn, constraints=constraints)

    def test_no_regulation_id_skips_regulation_check(self):
        with (
            patch("src.api.services.team_optimizer._build_pool",
                  return_value=self._pool()),
            patch("src.api.services.team_optimizer.regulation_service.get_regulation_info") as mock_info,
            patch("src.api.services.team_optimizer._validate_constraints"),
            patch("src.api.services.team_optimizer._apply_constraints",
                  return_value=self._pool()),
            patch("src.api.services.team_optimizer._sample_candidate") as mock_sc,
            patch("src.api.services.team_optimizer.analyze_team",
                  return_value=self._mock_analysis()),
            patch("src.api.services.team_optimizer._is_acceptable", return_value=True),
            patch("src.api.services.team_optimizer.load_build", return_value=MagicMock()),
            patch("src.api.services.team_optimizer.score_team",
                  return_value=self._mock_scoring()),
        ):
            mock_sc.return_value = (self._members(), [MagicMock()] * 6)
            conn = MagicMock()
            optimize_team(conn, constraints=GenerationConstraints(),
                          population_size=3, generations=1, rng=random.Random(42))
            mock_info.assert_not_called()
