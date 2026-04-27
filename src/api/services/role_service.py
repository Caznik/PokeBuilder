# src/api/services/role_service.py
"""Role detection for competitive Pokémon builds."""

from ..models.team import PokemonBuild

# ---------------------------------------------------------------------------
# Thresholds (computed stats at L100 using the set's EVs / nature)
# ---------------------------------------------------------------------------

SPEED_THRESHOLD     = 280
ATTACK_THRESHOLD    = 300
SP_ATTACK_THRESHOLD = 300
DEFENSE_THRESHOLD   = 200
HP_THRESHOLD        = 300

# ---------------------------------------------------------------------------
# Move-name sets for move-based role detection
# ---------------------------------------------------------------------------

HAZARD_SETTER_MOVES:  frozenset[str] = frozenset({
    "stealth-rock", "spikes", "toxic-spikes", "sticky-web",
})
HAZARD_REMOVAL_MOVES: frozenset[str] = frozenset({
    "defog", "rapid-spin", "mortal-spin",
})
PIVOT_MOVES: frozenset[str] = frozenset({
    "u-turn", "volt-switch", "flip-turn", "teleport",
})
SUPPORT_MOVES: frozenset[str] = frozenset({
    "toxic", "thunder-wave", "will-o-wisp", "wish",
    "heal-bell", "aromatherapy", "encore", "taunt",
})


# ---------------------------------------------------------------------------
# Role detection
# ---------------------------------------------------------------------------

def detect_roles(build: PokemonBuild) -> list[str]:
    """Assign competitive roles to a Pokémon build.

    Roles are not mutually exclusive — a Pokémon may hold several.

    Args:
        build: A fully loaded PokemonBuild with computed stats and moves.

    Returns:
        List of role strings (subset of physical_sweeper, special_sweeper,
        tank, hazard_setter, hazard_removal, pivot, support).
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
        roles.append("physical_sweeper")

    if (stats["sp_attack"] >= SP_ATTACK_THRESHOLD
            and stats["speed"] >= SPEED_THRESHOLD
            and mostly_special):
        roles.append("special_sweeper")

    if (stats["hp"] >= HP_THRESHOLD
            and (stats["defense"] >= DEFENSE_THRESHOLD
                 or stats["sp_defense"] >= DEFENSE_THRESHOLD)):
        roles.append("tank")

    if move_names & HAZARD_SETTER_MOVES:
        roles.append("hazard_setter")

    if move_names & HAZARD_REMOVAL_MOVES:
        roles.append("hazard_removal")

    if move_names & PIVOT_MOVES:
        roles.append("pivot")

    if move_names & SUPPORT_MOVES:
        roles.append("support")

    return roles
