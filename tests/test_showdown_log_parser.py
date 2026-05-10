# tests/test_showdown_log_parser.py
"""Unit tests for the Showdown battle log parser."""

import pytest

FIXTURE_LOG = """\
|j|☆Player1
|j|☆Player2
|gametype|doubles
|gen|9
|tier|[Gen 9 Champions] VGC 2026 Reg M-A
|clearpoke
|poke|p1|Koraidon, L50|
|poke|p1|Flutter Mane, L50|
|poke|p1|Incineroar, L50|
|poke|p1|Farigiraf, L50|
|poke|p1|Urshifu, L50|
|poke|p1|Rillaboom, L50|
|poke|p2|Miraidon, L50|
|poke|p2|Iron Hands, L50|
|poke|p2|Amoonguss, L50|
|poke|p2|Tornadus, L50|
|poke|p2|Landorus-Therian, L50|
|poke|p2|Urshifu, L50|
|teampreview
|start
|turn|1
|switch|p1a: Koraidon|Koraidon, L50|175/175
|switch|p1b: Incineroar|Incineroar, L50|155/155
|switch|p2a: Miraidon|Miraidon, L50|175/175
|switch|p2b: Amoonguss|Amoonguss, L50|207/207
|move|p1a: Koraidon|Collision Course|p2a: Miraidon
|-ability|p1a: Koraidon|Orichalcum Pulse|
|move|p1b: Incineroar|Fake Out|p2b: Amoonguss
|-item|p1b: Incineroar|Safety Goggles|
|turn|2
|switch|p1b: Urshifu|Urshifu, L50|165/165
|switch|p2b: Tornadus|Tornadus, L50|145/145
|-item|p1a: Koraidon|Booster Energy|
|move|p1a: Koraidon|Protect|p1a: Koraidon
|move|p2a: Miraidon|Dazzling Gleam|p1b: Urshifu
|move|p1b: Urshifu|Wicked Blow|p2a: Miraidon
|move|p2b: Tornadus|Tailwind|p2b: Tornadus
|turn|3
|win|Player1
"""


@pytest.fixture
def parsed():
    from src.ingestors.showdown_log_parser import parse_log
    return parse_log("test-id-001", "Player1", "Player2", FIXTURE_LOG)


class TestTeamPreview:
    def test_p1_team_has_six_pokemon(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        assert len(p1.team) == 6

    def test_p1_team_names_normalized(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        assert "koraidon" in p1.team
        assert "flutter-mane" in p1.team
        assert "incineroar" in p1.team

    def test_p2_team_has_six_pokemon(self, parsed):
        p2 = next(t for t in parsed.teams if t.player == "p2")
        assert len(p2.team) == 6

    def test_p2_team_includes_landorus_therian(self, parsed):
        p2 = next(t for t in parsed.teams if t.player == "p2")
        assert "landorus-therian" in p2.team


class TestBroughtAndLeads:
    def test_p1_brought_contains_switches(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        assert "koraidon" in p1.brought
        assert "incineroar" in p1.brought
        assert "urshifu" in p1.brought

    def test_p1_leads_are_turn1_switches(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        assert p1.leads == ["koraidon", "incineroar"]

    def test_p2_leads_are_turn1_switches(self, parsed):
        p2 = next(t for t in parsed.teams if t.player == "p2")
        assert p2.leads == ["miraidon", "amoonguss"]

    def test_brought_no_duplicates(self, parsed):
        for team in parsed.teams:
            assert len(team.brought) == len(set(team.brought))


class TestDetails:
    def test_moves_tracked_for_koraidon(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        kor = next(d for d in p1.details if d.pokemon == "koraidon")
        assert "collision-course" in kor.moves or "Collision Course" in kor.moves

    def test_item_tracked_for_incineroar(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        inc = next(d for d in p1.details if d.pokemon == "incineroar")
        assert inc.item == "Safety Goggles"

    def test_ability_tracked_for_koraidon(self, parsed):
        p1 = next(t for t in parsed.teams if t.player == "p1")
        kor = next(d for d in p1.details if d.pokemon == "koraidon")
        assert kor.ability == "Orichalcum Pulse"


class TestWinner:
    def test_winner_resolved_to_p1(self, parsed):
        assert parsed.winner == "p1"

    def test_replay_id_preserved(self, parsed):
        assert parsed.replay_id == "test-id-001"

    def test_player_names_preserved(self, parsed):
        assert parsed.p1 == "Player1"
        assert parsed.p2 == "Player2"


class TestNormalizeSpecies:
    def test_basic_lowercase(self):
        from src.ingestors.showdown_log_parser import _normalize_species
        assert _normalize_species("Koraidon, L50") == "koraidon"

    def test_spaces_become_hyphens(self):
        from src.ingestors.showdown_log_parser import _normalize_species
        assert _normalize_species("Flutter Mane, L50") == "flutter-mane"

    def test_landorus_therian(self):
        from src.ingestors.showdown_log_parser import _normalize_species
        assert _normalize_species("Landorus-Therian, L50") == "landorus-therian"

    def test_apostrophe_stripped(self):
        from src.ingestors.showdown_log_parser import _normalize_species
        assert _normalize_species("Farfetch'd, L50") == "farfetchd"
