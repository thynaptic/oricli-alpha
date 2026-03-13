import math

from oricli_core.brain.modules.game_theory_solver import GameTheorySolver


def test_solve_game_prisoners_dilemma_equilibrium_is_defect_defect() -> None:
    mod = GameTheorySolver()
    result = mod.execute("analyze_scenario", {"scenario": "prisoners_dilemma"})

    assert result["success"] is True
    equilibria = result["equilibria"]
    # Prisoner's dilemma should have a single pure NE: (D, D)
    assert len(equilibria) == 1
    eq = equilibria[0]
    assert eq["type"] == "pure"
    assert eq["strategies"]["A"] == "D"
    assert eq["strategies"]["B"] == "D"


def test_best_response_matches_solve_game_for_simple_2x2() -> None:
    # Coordination game with two equilibria (X, X) and (Y, Y)
    mod = GameTheorySolver()
    params = {
        "players": ["A", "B"],
        "strategies": {"A": ["X", "Y"], "B": ["X", "Y"]},
        "payoffs": [
            # A:X
            [
                [2, 2],  # B:X
                [0, 0],  # B:Y
            ],
            # A:Y
            [
                [0, 0],  # B:X
                [1, 1],  # B:Y
            ],
        ],
    }

    res_eq = mod.execute("solve_game", params)
    assert res_eq["success"] is True
    equilibria = res_eq["equilibria"]
    # Two pure equilibria
    profiles = {
        (eq["strategies"]["A"], eq["strategies"]["B"])
        for eq in equilibria
    }
    assert profiles == {("X", "X"), ("Y", "Y")}

    # Best response for A given B plays X: A should play X
    br_a = mod.execute(
        "best_response",
        {
            **params,
            "player": "A",
            "profile": {"B": "X"},
        },
    )
    assert br_a["success"] is True
    assert br_a["best_responses"] == ["X"]

    # Best response for B given A plays Y: B should play Y
    br_b = mod.execute(
        "best_response",
        {
            **params,
            "player": "B",
            "profile": {"A": "Y"},
        },
    )
    assert br_b["success"] is True
    assert br_b["best_responses"] == ["Y"]


def test_solve_game_rejects_too_many_profiles() -> None:
    mod = GameTheorySolver()
    # 6 players with 6 strategies each would exceed the MAX_PROFILES guard,
    # but we respect the module's own MAX_* constants to keep this future-proof.
    max_players = mod.MAX_PLAYERS
    max_strategies = mod.MAX_STRATEGIES_PER_PLAYER

    players = [f"P{i}" for i in range(max_players)]
    strategies = {p: [f"s{j}" for j in range(max_strategies)] for p in players}

    # Construct a dummy payoff tensor lazily if needed by a future test; we
    # rely on the normalization guard to fail before indexing.
    params = {
        "players": players,
        "strategies": strategies,
        "payoffs": 0,  # intentionally invalid; should never be dereferenced
    }

    try:
        mod.execute("solve_game", params)
        # If we did not raise, something is off with the guard
        assert False, "Expected InvalidParameterError for too many profiles"
    except Exception as exc:  # noqa: BLE001
        # We do not import the concrete exception type here to keep the test
        # decoupled; we only assert that some error was raised.
        assert "too many strategy profiles" in str(exc)

