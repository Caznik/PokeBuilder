# tests/test_role_service.py
"""Unit tests for VGC doubles role detection."""

import pytest
from src.api.models.team import MoveDetail, PokemonBuild
from src.api.services.role_service import detect_roles

BASE_STATS = {"hp": 250, "attack": 200, "defense": 150, "sp_attack": 150, "sp_defense": 150, "speed": 200}


def _build(stats=None, moves=None):
    s = {**BASE_STATS, **(stats or {})}
    return PokemonBuild(
        pokemon_name="test", set_id=1, types=["normal"],
        nature="hardy", ability=None, item=None,
        stats=s, moves=moves or [],
    )

def _phys(name="tackle"):    return MoveDetail(name, "normal", "physical")
def _spec(name="flamethrower"): return MoveDetail(name, "fire", "special")
def _status(name="toxic"):   return MoveDetail(name, "poison", "status")


class TestPhysicalAttacker:
    def test_detected_when_high_attack_speed_and_physical_moves(self):
        build = _build(stats={"attack": 350, "speed": 310}, moves=[_phys(), _phys(), _phys(), _status()])
        assert "physical_attacker" in detect_roles(build)

    def test_not_detected_when_attack_too_low(self):
        build = _build(stats={"attack": 250, "speed": 310}, moves=[_phys(), _phys(), _phys(), _status()])
        assert "physical_attacker" not in detect_roles(build)

    def test_not_detected_when_speed_too_low(self):
        build = _build(stats={"attack": 350, "speed": 200}, moves=[_phys(), _phys(), _phys(), _status()])
        assert "physical_attacker" not in detect_roles(build)

    def test_old_name_not_returned(self):
        build = _build(stats={"attack": 350, "speed": 310}, moves=[_phys(), _phys(), _phys(), _status()])
        assert "physical_sweeper" not in detect_roles(build)


class TestSpecialAttacker:
    def test_detected_when_high_sp_attack_and_speed(self):
        build = _build(stats={"sp_attack": 350, "speed": 310}, moves=[_spec(), _spec(), _spec(), _status()])
        assert "special_attacker" in detect_roles(build)

    def test_not_detected_when_sp_attack_too_low(self):
        build = _build(stats={"sp_attack": 200, "speed": 310}, moves=[_spec(), _spec(), _spec(), _status()])
        assert "special_attacker" not in detect_roles(build)

    def test_old_name_not_returned(self):
        build = _build(stats={"sp_attack": 350, "speed": 310}, moves=[_spec(), _spec(), _spec(), _status()])
        assert "special_sweeper" not in detect_roles(build)


class TestTailwindSetter:
    def test_detected_when_has_tailwind(self):
        build = _build(moves=[_status("tailwind")])
        assert "tailwind_setter" in detect_roles(build)

    def test_not_detected_without_tailwind(self):
        build = _build(moves=[_status("toxic")])
        assert "tailwind_setter" not in detect_roles(build)

    def test_also_gets_speed_control(self):
        build = _build(moves=[_status("tailwind")])
        roles = detect_roles(build)
        assert "tailwind_setter" in roles
        assert "speed_control" in roles


class TestTrickRoomSetter:
    def test_detected_when_has_trick_room(self):
        build = _build(moves=[_status("trick-room")])
        assert "trick_room_setter" in detect_roles(build)

    def test_not_detected_without_trick_room(self):
        build = _build(moves=[_status("tailwind")])
        assert "trick_room_setter" not in detect_roles(build)

    def test_also_gets_speed_control(self):
        build = _build(moves=[_status("trick-room")])
        roles = detect_roles(build)
        assert "trick_room_setter" in roles
        assert "speed_control" in roles


class TestFakeOutUser:
    def test_detected_when_has_fake_out(self):
        build = _build(moves=[_phys("fake-out")])
        assert "fake_out_user" in detect_roles(build)

    def test_also_gets_disruption(self):
        build = _build(moves=[_phys("fake-out")])
        roles = detect_roles(build)
        assert "fake_out_user" in roles
        assert "disruption" in roles


class TestRedirector:
    def test_detected_for_follow_me(self):
        build = _build(moves=[_status("follow-me")])
        assert "redirector" in detect_roles(build)

    def test_detected_for_rage_powder(self):
        build = _build(moves=[_status("rage-powder")])
        assert "redirector" in detect_roles(build)

    def test_also_gets_disruption(self):
        build = _build(moves=[_status("follow-me")])
        roles = detect_roles(build)
        assert "redirector" in roles
        assert "disruption" in roles


class TestSpreadAttacker:
    def test_detected_for_earthquake(self):
        build = _build(moves=[_phys("earthquake")])
        assert "spread_attacker" in detect_roles(build)

    def test_detected_for_discharge(self):
        build = _build(moves=[_spec("discharge")])
        assert "spread_attacker" in detect_roles(build)

    def test_detected_for_heat_wave(self):
        build = _build(moves=[_spec("heat-wave")])
        assert "spread_attacker" in detect_roles(build)

    def test_not_detected_without_spread_move(self):
        build = _build(moves=[_phys("tackle")])
        assert "spread_attacker" not in detect_roles(build)


class TestRemovedRoles:
    def test_hazard_setter_never_detected(self):
        build = _build(moves=[_status("stealth-rock")])
        assert "hazard_setter" not in detect_roles(build)

    def test_hazard_removal_never_detected(self):
        build = _build(moves=[_status("defog")])
        assert "hazard_removal" not in detect_roles(build)

    def test_pivot_never_detected(self):
        build = _build(moves=[_phys("u-turn")])
        assert "pivot" not in detect_roles(build)


class TestSpeedControlComposite:
    def test_not_assigned_without_setter(self):
        build = _build(moves=[_phys("earthquake")])
        assert "speed_control" not in detect_roles(build)

    def test_only_one_speed_control_entry_when_tailwind_and_tr(self):
        build = _build(moves=[_status("tailwind"), _status("trick-room")])
        roles = detect_roles(build)
        assert roles.count("speed_control") == 1


class TestDisruptionComposite:
    def test_not_assigned_without_disruption_move(self):
        build = _build(moves=[_status("tailwind")])
        assert "disruption" not in detect_roles(build)
