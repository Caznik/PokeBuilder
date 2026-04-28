# Sprint 8 Documentation

## Overview

This document covers all components created during Sprint 8 of the PokeBuilder project — the Team Scoring Engine. This sprint transforms the system from generator + validator into **generator → evaluator → ranker**: every team receives a numeric quality score with a per-component breakdown that explains why it ranks where it does.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture](#architecture)
3. [Score Scale](#score-scale)
4. [Component Scores](#component-scores)
5. [Aggregation](#aggregation)
6. [Explainability](#explainability)
7. [Sprint 7 Integration](#sprint-7-integration)
8. [REST API](#rest-api)
9. [Testing Strategy](#testing-strategy)
10. [Files Created / Modified](#files-created--modified)

---

## Feature Overview

Before this sprint the generator ranked accepted teams using a single signal — the worst weakness count. Two teams with the same maximum weakness received identical scores even when one had clearly better offensive coverage, role distribution, or speed control.

**Core capabilities added:**
- Four independent component scores (coverage, defensive, role, speed), each bounded to `[0.0, 1.0]` and paired with a rationale string.
- A weighted aggregate score on a `[0.0, 10.0]` scale.
- `POST /team/score` — score any 6-member team on demand.
- `POST /team/generate` updated — accepted candidates are now ranked by the multi-component score, and the `breakdown` is included in the response.

---

## Architecture

```
POST /team/score  [{pokemon_name, set_id} × 6]
    ↓  team_loader.load_team(conn, members)         (Sprint 6)
    ↓  team_analysis.analyze_team(builds)           (Sprint 6)
    ↓  team_scorer.score_team(report, builds)       (Sprint 8)
    │     ├── compute_coverage_score(report)        → {score, reason}
    │     ├── compute_defensive_score(report)       → {score, reason}
    │     ├── compute_role_score(report)            → {score, reason}
    │     └── compute_speed_score(builds)           → {score, reason}
    ↓  weighted average × 10                        → 0–10
    ↓  ScoreResponse  {score, breakdown, analysis}

POST /team/generate
    ↓  ... Sprint 7 pipeline ...
    ↓  for each accepted team: score_team(report, builds)
    ↓  sort by score desc
    ↓  GenerationResponse with breakdown in each TeamResult
```

`team_scorer.py` owns all scoring logic. Routes and the generator consume it — no duplication.

---

## Score Scale

- **Component scores:** each in `[0.0, 1.0]`, paired with a rationale string.
- **Final score:** in `[0.0, 10.0]`, computed as `round((weighted_avg × 10), 2)`.
- **No separate penalty term.** Each component encodes its own penalties within its 0–1 calculation.

---

## Component Scores

### `compute_coverage_score(report) → dict`

```python
covered = len(report["coverage"]["covered_types"])
missing = report["coverage"]["missing_types"]
score   = covered / 18

if not missing:
    reason = "covers all 18 types"
else:
    reason = f"missing {', '.join(sorted(missing))}"
```

Range: 0.0 (no coverage) to 1.0 (all 18 types). Missing types are listed in sorted order so the rationale is stable and comparable across teams.

---

### `compute_defensive_score(report) → dict`

```python
weaknesses   = report["weaknesses"]               # {type: count}
worst_type   = max(weaknesses, key=weaknesses.get) if weaknesses else None
worst_count  = weaknesses[worst_type] if worst_type else 0
score        = max(0.0, 1.0 - worst_count * 0.2)

if not weaknesses:
    reason = "no shared weaknesses"
else:
    reason = f"{worst_count} Pokémon weak to {worst_type}"
```

| Worst count | Score |
|---|---|
| 0 | 1.0 |
| 1 | 0.8 |
| 2 | 0.6 |
| 3 | 0.4 |
| 4 | 0.2 |
| 5+ | 0.0 (clamped) |

The 0.2 penalty per count (steeper than Sprint 7's 0.05) is justified because the defensive component is now the only signal carrying weakness information. The rationale names the worst type — the one that most needs explaining.

---

### `compute_role_score(report) → dict`

```python
rules_met = sum(
    1 for rule, minimum in TEAM_RULES.items()
    if report["roles"].get(_RULE_TO_ROLE[rule], 0) >= minimum
)
score = rules_met / len(TEAM_RULES)

if not report["issues"]:
    reason = "all role minimums met"
else:
    reason = "; ".join(report["issues"])
```

There are 5 rules in `TEAM_RULES`. For accepted teams (which pass all rules) the score is always 1.0 and the reason is `"all role minimums met"`. For arbitrary teams scored via `/team/score`, the rationale reuses Sprint 6's `issues` strings — single source of truth, no parallel formatting logic.

---

### `compute_speed_score(builds) → dict` *(new)*

```python
SPEED_THRESHOLD = 280   # imported from role_service
PRIORITY_MOVES  = frozenset({
    "extreme-speed", "sucker-punch", "bullet-punch", "mach-punch",
    "ice-shard", "aqua-jet", "vacuum-wave", "accelerock",
    "jet-punch", "thunderclap", "quick-attack", "shadow-sneak",
})

fast     = count of builds where stats["speed"] >= SPEED_THRESHOLD
priority = count of builds with at least one move in PRIORITY_MOVES

if fast == 0 and priority == 0:
    score, reason = 0.0, "no fast Pokémon and no priority moves"
elif fast >= 2 or (fast >= 1 and priority >= 1):
    score  = 1.0
    reason = f"{fast} fast Pokémon, {priority} priority user(s)"
else:
    score  = 0.5
    reason = f"limited speed control ({fast} fast, {priority} priority)"
```

A team with no speed control is helpless against opposing offence (0.0). Two fast Pokémon, or one fast + one priority user, provides solid speed control (1.0). Anything in between scores 0.5.

`PRIORITY_MOVES` lives in `role_service.py` alongside `SPEED_THRESHOLD` — same domain (speed/priority is move-driven role information), single source of truth.

---

## Aggregation

```python
WEIGHTS = {
    "coverage":  1.0,
    "defensive": 1.5,   # weaknesses dominate competitive viability
    "role":      1.2,
    "speed":     1.0,
}

def score_team(report, builds):
    breakdown = {
        "coverage":  compute_coverage_score(report),
        "defensive": compute_defensive_score(report),
        "role":      compute_role_score(report),
        "speed":     compute_speed_score(builds),
    }
    weighted_sum = sum(WEIGHTS[k] * breakdown[k]["score"] for k in breakdown)
    total_weight = sum(WEIGHTS.values())   # 4.7
    score = round((weighted_sum / total_weight) * 10, 2)
    return {"score": score, "breakdown": breakdown}
```

Only `breakdown[k]["score"]` enters the arithmetic — rationale strings flow through untouched.

---

## Explainability

A score of `8.2/10` alone is not a recommendation — it is a number. Every component therefore returns a **rationale string** alongside its numeric score. Rationale examples:

| Component | Example reason |
|---|---|
| coverage | `"missing fairy, dragon, ice"` |
| defensive | `"2 Pokémon weak to ground"` |
| role | `"all role minimums met"` |
| speed | `"no fast Pokémon and no priority moves"` |

Rationales are derived from the **same inputs** as the corresponding numeric score — no separate explanation logic. This guarantees the explanation cannot drift from the math.

---

## Sprint 7 Integration

`team_generator.py`:
- `_score_team` (Sprint 7's `1.0 - max_weakness * 0.05`) removed.
- `score_team(report, builds)` from `team_scorer` called for each accepted candidate.
- Each result dict gains `breakdown`; sorting still keys on `score` descending.
- Score is now in the 0–10 range, not 0–1.

`models/generation.py`:
- `TeamResult` gains `breakdown: ScoreBreakdown`.
- `score` field type unchanged (float), value range now 0–10.

`routes/generation.py`:
- Constructs `ScoreBreakdown` and `ScoreComponent` objects from the result dict before building `TeamResult`.

---

## REST API

### `POST /team/score`

**File:** `src/api/routes/scoring.py`

**Request** — same shape as `/team/analyze`:
```json
[
  {"pokemon_name": "garchomp", "set_id": 1},
  {"pokemon_name": "ferrothorn", "set_id": 2},
  {"pokemon_name": "rotom-wash", "set_id": 3},
  {"pokemon_name": "clefable", "set_id": 4},
  {"pokemon_name": "heatran", "set_id": 5},
  {"pokemon_name": "landorus", "set_id": 6}
]
```

**Response 200:**
```json
{
  "score": 8.21,
  "breakdown": {
    "coverage":  {"score": 0.83, "reason": "missing fairy, dragon, ice"},
    "defensive": {"score": 0.80, "reason": "1 Pokémon weak to ground"},
    "role":      {"score": 1.00, "reason": "all role minimums met"},
    "speed":     {"score": 1.00, "reason": "2 fast Pokémon, 1 priority user(s)"}
  },
  "analysis": {
    "valid": true,
    "issues": [],
    "roles": {"physical_sweeper": 2, "special_sweeper": 1, "tank": 1, "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0},
    "weaknesses": {"ground": 1},
    "resistances": {"steel": 3},
    "coverage": {
      "covered_types": ["grass", "steel", "fire"],
      "missing_types": ["fairy", "dragon", "ice"]
    }
  }
}
```

The full Sprint 6 analysis is included — scoring already required computing it, and returning it lets callers explain the score without a second API call.

**Response 422** — Team does not have exactly 6 members.  
**Response 404** — Set ID not found or does not belong to the named Pokémon.

---

### `POST /team/generate` (updated)

`TeamResult` gains `breakdown` with the same shape as `/team/score`:

```json
{
  "teams": [
    {
      "score": 8.21,
      "breakdown": {
        "coverage":  {"score": 0.83, "reason": "missing fairy, dragon, ice"},
        "defensive": {"score": 0.80, "reason": "1 Pokémon weak to ground"},
        "role":      {"score": 1.00, "reason": "all role minimums met"},
        "speed":     {"score": 1.00, "reason": "2 fast Pokémon, 1 priority user(s)"}
      },
      "members": [...],
      "analysis": {...}
    }
  ],
  "generated": 47,
  "valid_found": 5
}
```

### Pydantic Models (`src/api/models/scoring.py`)

| Model | Fields |
|---|---|
| `ScoreComponent` | `score` (float), `reason` (str) |
| `ScoreBreakdown` | `coverage`, `defensive`, `role`, `speed` (each a `ScoreComponent`) |
| `ScoreResponse` | `score` (float), `breakdown` (ScoreBreakdown), `analysis` (TeamAnalysisResponse) |

---

## Testing Strategy

| File | Tests | Approach |
|---|---|---|
| `tests/test_team_scorer.py` | 42 | Pure-function tests for all four `compute_*_score` functions and `score_team` aggregation; asserts both numeric score and reason string content; sanity check that a clearly good team outscores a clearly bad one |
| `tests/test_score_api.py` | 14 | FastAPI `TestClient`; mocks `load_team`, `analyze_team`, `score_team`; asserts response shape, 422/404 error codes, and field types |
| `tests/test_team_generator.py` | 3 updated | Replaced `TestScoreTeam` (old formula) with `test_team_dict_has_score_members_analysis_breakdown` and `test_score_is_in_0_to_10_range` |
| `tests/test_generation_api.py` | 2 added | `test_team_has_breakdown_with_four_components` and `test_breakdown_components_have_score_and_reason` |

**Total new/updated tests: 58 (357 total, all passing)**

```bash
pytest tests/test_team_scorer.py tests/test_score_api.py -v
```

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `src/api/services/team_scorer.py` | `compute_coverage_score`, `compute_defensive_score`, `compute_role_score`, `compute_speed_score`, `score_team`, `WEIGHTS` |
| `src/api/models/scoring.py` | `ScoreComponent`, `ScoreBreakdown`, `ScoreResponse` Pydantic models |
| `src/api/routes/scoring.py` | `POST /team/score` route |
| `tests/test_team_scorer.py` | 42 scoring service unit tests |
| `tests/test_score_api.py` | 14 scoring API integration tests |
| `documentation/sprint_8_documentation.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `src/api/services/role_service.py` | Added `PRIORITY_MOVES` frozenset (12 priority moves) |
| `src/api/models/generation.py` | `TeamResult` gains `breakdown: ScoreBreakdown` |
| `src/api/routes/generation.py` | Constructs `ScoreBreakdown` from result and passes to `TeamResult` |
| `src/api/services/team_generator.py` | Removed `_score_team`; calls `score_team(report, builds)`; result includes `breakdown` |
| `src/api/routes/__init__.py` | Exported `scoring_router` |
| `src/api/main.py` | Registered `scoring_router` |
| `tests/test_team_generator.py` | Removed `TestScoreTeam`; added `breakdown` and 0–10 range assertions |
| `tests/test_generation_api.py` | Added `breakdown` to mock data; added two new breakdown tests |

---

## Summary

Sprint 8 successfully delivered:

1. **Four component scores** — coverage, defensive, role (all consuming Sprint 6 analysis), and speed (new, move-aware)
2. **Rationale strings** — every component returns a short factual reason derived from the same data as its score
3. **Weighted aggregation** — 0–10 scale with tuneable weights; defensive weighted 1.5× (the dominant signal for competitive viability)
4. **`POST /team/score`** — score any 6-member team on demand; returns score, full breakdown, and Sprint 6 analysis
5. **Generator upgrade** — Sprint 7's weakness-only score replaced; accepted teams now ranked by the multi-component scorer with `breakdown` in the response
6. **58 new/updated tests** — 357 total, all passing

The system now supports:
- ✅ Pokémon data (Sprint 1)
- ✅ Abilities and relationships (Sprint 1)
- ✅ Types and effectiveness (Sprints 1–3)
- ✅ Moves and learnsets (Sprint 2)
- ✅ Stat calculation with IVs, EVs, Natures (Sprint 4)
- ✅ Competitive sets from Smogon (Sprint 5)
- ✅ Team role analysis, validation, weakness/coverage report (Sprint 6)
- ✅ Autonomous team generation with constraints and scoring (Sprint 7)
- ✅ Multi-component team scoring engine with explainable breakdown (Sprint 8)

---

*Last updated: April 28, 2026*
