# tests/test_role_service.py
"""Unit tests for role detection."""

import pytest
from src.api.models.team import MoveDetail, PokemonBuild
from src.api.services.role_service import detect_roles

# ---------------------------------------------------------------------------
# Build factories
# ---------------------------------------------------------------------------

BASE_STATS = {"hp": 250, "attack": 200, "defense": 150, "sp_attack": 150, "sp_defense": 150, "speed": 200}


def _build(stats=None, moves=None, types=None):
    s = {**BASE_STATS, **(stats or {})}
    return PokemonBuild(
        pokemon_name="test", set_id=1,
        types=types or ["normal"],
        nature="hardy", ability=None, item=None,
        stats=s, moves=moves or [],
    )


def _phys(name="tackle", type_="normal"):
    return MoveDetail(name, type_, "physical")


def _spec(name="flamethrower", type_="fire"):
    return MoveDetail(name, type_, "special")


def _status(name="toxic", type_="poison"):
    return MoveDetail(name, type_, "status")


class TestPhysicalSweeper:

    def test_detected_when_high_attack_speed_and_physical_moves(self):
        build = _build(
            stats={"attack": 350, "speed": 310},
            moves=[_phys(), _phys(), _phys(), _status()],
        )
        assert "physical_sweeper" in detect_roles(build)

    def test_not_detected_when_attack_too_low(self):
        build = _build(
            stats={"attack": 250, "speed": 310},
            moves=[_phys(), _phys(), _phys(), _status()],
        )
        assert "physical_sweeper" not in detect_roles(build)

    def test_not_detected_when_speed_too_low(self):
        build = _build(
            stats={"attack": 350, "speed": 200},
            moves=[_phys(), _phys(), _phys(), _status()],
        )
        assert "physical_sweeper" not in detect_roles(build)

    def test_not_detected_when_mostly_special_moves(self):
        build = _build(
            stats={"attack": 350, "speed": 310},
            moves=[_spec(), _spec(), _spec(), _phys()],
        )
        assert "physical_sweeper" not in detect_roles(build)


class TestSpecialSweeper:

    def test_detected_when_high_spa_speed_and_special_moves(self):
        build = _build(
            stats={"sp_attack": 350, "speed": 310},
            moves=[_spec(), _spec(), _spec(), _status()],
        )
        assert "special_sweeper" in detect_roles(build)

    def test_not_detected_when_sp_attack_too_low(self):
        build = _build(
            stats={"sp_attack": 250, "speed": 310},
            moves=[_spec(), _spec(), _spec(), _status()],
        )
        assert "special_sweeper" not in detect_roles(build)

    def test_not_detected_when_mostly_physical_moves(self):
        build = _build(
            stats={"sp_attack": 350, "speed": 310},
            moves=[_phys(), _phys(), _phys(), _spec()],
        )
        assert "special_sweeper" not in detect_roles(build)


class TestTank:

    def test_detected_with_high_hp_and_defense(self):
        build = _build(stats={"hp": 350, "defense": 250})
        assert "tank" in detect_roles(build)

    def test_detected_with_high_hp_and_sp_defense(self):
        build = _build(stats={"hp": 350, "sp_defense": 250})
        assert "tank" in detect_roles(build)

    def test_not_detected_when_hp_too_low(self):
        build = _build(stats={"hp": 200, "defense": 250})
        assert "tank" not in detect_roles(build)

    def test_not_detected_when_both_defenses_low(self):
        build = _build(stats={"hp": 350, "defense": 150, "sp_defense": 150})
        assert "tank" not in detect_roles(build)


class TestMoveBasedRoles:

    def test_hazard_setter_stealth_rock(self):
        build = _build(moves=[MoveDetail("stealth-rock", "rock", "status")])
        assert "hazard_setter" in detect_roles(build)

    def test_hazard_setter_spikes(self):
        build = _build(moves=[MoveDetail("spikes", "ground", "status")])
        assert "hazard_setter" in detect_roles(build)

    def test_hazard_removal_defog(self):
        build = _build(moves=[MoveDetail("defog", "flying", "status")])
        assert "hazard_removal" in detect_roles(build)

    def test_hazard_removal_rapid_spin(self):
        build = _build(moves=[MoveDetail("rapid-spin", "normal", "physical")])
        assert "hazard_removal" in detect_roles(build)

    def test_pivot_u_turn(self):
        build = _build(moves=[MoveDetail("u-turn", "bug", "physical")])
        assert "pivot" in detect_roles(build)

    def test_pivot_volt_switch(self):
        build = _build(moves=[MoveDetail("volt-switch", "electric", "special")])
        assert "pivot" in detect_roles(build)

    def test_support_toxic(self):
        build = _build(moves=[MoveDetail("toxic", "poison", "status")])
        assert "support" in detect_roles(build)

    def test_support_wish(self):
        build = _build(moves=[MoveDetail("wish", "normal", "status")])
        assert "support" in detect_roles(build)


class TestMultipleRoles:

    def test_ferrothorn_like_gets_tank_and_hazard_setter(self):
        """High HP+Def + stealth rock → tank + hazard_setter."""
        build = _build(
            stats={"hp": 360, "defense": 280, "sp_defense": 200, "speed": 50},
            moves=[
                MoveDetail("stealth-rock", "rock", "status"),
                MoveDetail("leech-seed",   "grass", "status"),
                MoveDetail("power-whip",   "grass", "physical"),
                MoveDetail("knock-off",    "dark",  "physical"),
            ],
        )
        roles = detect_roles(build)
        assert "tank" in roles
        assert "hazard_setter" in roles

    def test_no_moves_gives_no_move_roles(self):
        build = _build(moves=[])
        roles = detect_roles(build)
        assert "hazard_setter" not in roles
        assert "pivot" not in roles
        assert "support" not in roles
