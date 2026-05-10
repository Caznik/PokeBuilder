# src/ingestors/showdown_log_parser.py
"""Parse Pokémon Showdown battle replay logs into structured data."""

from dataclasses import dataclass, field


@dataclass
class ParsedPokemonDetail:
    pokemon: str
    moves: list[str] = field(default_factory=list)
    item: str | None = None
    ability: str | None = None


@dataclass
class ParsedTeam:
    player: str
    team: list[str] = field(default_factory=list)
    brought: list[str] = field(default_factory=list)
    leads: list[str] = field(default_factory=list)
    details: list[ParsedPokemonDetail] = field(default_factory=list)


@dataclass
class ParsedReplay:
    replay_id: str
    p1: str
    p2: str
    winner: str
    teams: list[ParsedTeam]


def _normalize_species(raw: str) -> str:
    """Extract normalized species name from Showdown log notation.

    Args:
        raw: Raw string, e.g. "Flutter Mane, L50" or "Landorus-Therian, L50".

    Returns:
        Lowercase hyphenated name, e.g. "flutter-mane".
    """
    name = raw.split(",")[0].strip()
    name = name.lower().replace(" ", "-").replace("'", "").replace(".", "")
    return name


def parse_log(replay_id: str, p1: str, p2: str, log: str) -> ParsedReplay:
    """Parse a Showdown battle log into structured data.

    Args:
        replay_id: Showdown replay ID.
        p1: Player 1 username.
        p2: Player 2 username.
        log: Raw Showdown protocol log string.

    Returns:
        ParsedReplay with teams, brought, leads, moves, items, abilities,
        and winner.
    """
    teams: dict[str, ParsedTeam] = {
        "p1": ParsedTeam(player="p1"),
        "p2": ParsedTeam(player="p2"),
    }
    details: dict[str, dict[str, ParsedPokemonDetail]] = {"p1": {}, "p2": {}}
    slot_species: dict[str, str] = {}   # "p1a" → normalized species
    brought_seen: dict[str, set[str]] = {"p1": set(), "p2": set()}
    winner: str | None = None
    current_turn = 0

    for line in log.splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        cmd = parts[1]

        if cmd == "poke" and len(parts) >= 4:
            player = parts[2]
            species = _normalize_species(parts[3])
            if player in teams and species not in teams[player].team:
                teams[player].team.append(species)

        elif cmd == "turn" and len(parts) >= 3:
            try:
                current_turn = int(parts[2])
            except ValueError:
                pass

        elif cmd in ("switch", "drag") and len(parts) >= 4:
            slot_full = parts[2]        # "p1a: Koraidon"
            slot_key = slot_full[:3]    # "p1a"
            player = slot_key[:2]       # "p1"
            species = _normalize_species(parts[3])
            slot_species[slot_key] = species
            if player in teams:
                if species not in brought_seen[player]:
                    brought_seen[player].add(species)
                    teams[player].brought.append(species)
                if current_turn == 1 and len(teams[player].leads) < 2:
                    teams[player].leads.append(species)
                if species not in details[player]:
                    details[player][species] = ParsedPokemonDetail(pokemon=species)

        elif cmd == "move" and len(parts) >= 4:
            slot_key = parts[2][:3]
            player = slot_key[:2]
            move = parts[3]
            species = slot_species.get(slot_key)
            if species and player in details and species in details[player]:
                d = details[player][species]
                if move not in d.moves:
                    d.moves.append(move)

        elif cmd == "-item" and len(parts) >= 4:
            slot_key = parts[2][:3]
            player = slot_key[:2]
            item = parts[3]
            species = slot_species.get(slot_key)
            if species and player in details and species in details[player]:
                details[player][species].item = item

        elif cmd == "-ability" and len(parts) >= 4:
            slot_key = parts[2][:3]
            player = slot_key[:2]
            ability = parts[3]
            species = slot_species.get(slot_key)
            if species and player in details and species in details[player]:
                details[player][species].ability = ability

        elif cmd == "win" and len(parts) >= 3:
            winner_name = parts[2]
            if winner_name == p1:
                winner = "p1"
            elif winner_name == p2:
                winner = "p2"

    for player_key, team in teams.items():
        team.details = list(details[player_key].values())

    return ParsedReplay(
        replay_id=replay_id,
        p1=p1,
        p2=p2,
        winner=winner or "p1",
        teams=[teams["p1"], teams["p2"]],
    )
