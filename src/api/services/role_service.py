# src/api/services/role_service.py
"""Role detection for competitive VGC doubles Pokémon builds."""

from ..models.team import PokemonBuild

# ---------------------------------------------------------------------------
# Stat thresholds (computed stats at L100 with set EVs / nature)
# ---------------------------------------------------------------------------

SPEED_THRESHOLD     = 280
ATTACK_THRESHOLD    = 300
SP_ATTACK_THRESHOLD = 300
DEFENSE_THRESHOLD   = 200
HP_THRESHOLD        = 300

# Speed thresholds for doubles archetype scoring (computed stats)
TAILWIND_SPEED_THRESHOLD = 200  # above this: benefits from Tailwind
TR_SPEED_THRESHOLD       = 150  # below this: benefits from Trick Room

# ---------------------------------------------------------------------------
# Move-name sets for move-based role detection
# ---------------------------------------------------------------------------

TAILWIND_MOVES: frozenset[str] = frozenset({"tailwind"})
TRICK_ROOM_MOVES: frozenset[str] = frozenset({"trick-room"})
FAKE_OUT_MOVES: frozenset[str] = frozenset({"fake-out"})
REDIRECTION_MOVES: frozenset[str] = frozenset({"follow-me", "rage-powder"})
SPREAD_MOVES: frozenset[str] = frozenset({
    "earthquake", "discharge", "heat-wave", "blizzard",
    "surf", "muddy-water", "rock-slide", "hyper-voice",
    "sludge-wave", "dazzling-gleam", "breaking-swipe",
})
SUPPORT_MOVES: frozenset[str] = frozenset({
    "toxic", "thunder-wave", "will-o-wisp", "wish",
    "heal-bell", "aromatherapy", "encore", "taunt",
    "light-screen", "reflect", "helping-hand",
})

# ---------------------------------------------------------------------------
# Role detection
# ---------------------------------------------------------------------------

def detect_roles(build: PokemonBuild) -> list[str]:
    """Assign VGC doubles competitive roles to a Pokémon build.

    Roles are not mutually exclusive — a Pokémon may hold several.
    Composite roles (speed_control, disruption) are also assigned when
    their constituent specific roles are detected.

    Args:
        build: A fully loaded PokemonBuild with computed stats and moves.

    Returns:
        List of role strings. Possible values: physical_attacker,
        special_attacker, tank, tailwind_setter, trick_room_setter,
        fake_out_user, redirector, spread_attacker, support,
        speed_control (composite), disruption (composite).
    """
    roles: list[str] = []
    stats = build.stats
    move_names = {m.name for m in build.moves}

    damaging = [m for m in build.moves if m.category != "status"]
    physical_count = sum(1 for m in damaging if m.category == "physical")
    special_count  = sum(1 for m in damaging if m.category == "special")
    mostly_physical = physical_count > special_count
    mostly_special  = special_count > physical_count

    if (stats["attack"] >= ATTACK_THRESHOLD
            and stats["speed"] >= SPEED_THRESHOLD
            and mostly_physical):
        roles.append("physical_attacker")

    if (stats["sp_attack"] >= SP_ATTACK_THRESHOLD
            and stats["speed"] >= SPEED_THRESHOLD
            and mostly_special):
        roles.append("special_attacker")

    if (stats["hp"] >= HP_THRESHOLD
            and (stats["defense"] >= DEFENSE_THRESHOLD
                 or stats["sp_defense"] >= DEFENSE_THRESHOLD)):
        roles.append("tank")

    has_speed_control = False

    if move_names & TAILWIND_MOVES:
        roles.append("tailwind_setter")
        has_speed_control = True

    if move_names & TRICK_ROOM_MOVES:
        roles.append("trick_room_setter")
        has_speed_control = True

    if has_speed_control:
        roles.append("speed_control")

    has_disruption = False

    if move_names & FAKE_OUT_MOVES:
        roles.append("fake_out_user")
        has_disruption = True

    if move_names & REDIRECTION_MOVES:
        roles.append("redirector")
        has_disruption = True

    if has_disruption:
        roles.append("disruption")

    if move_names & SPREAD_MOVES:
        roles.append("spread_attacker")

    if move_names & SUPPORT_MOVES:
        roles.append("support")

    return roles
