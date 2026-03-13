from __future__ import annotations

"""
Game Theory Solver Module

Symbolic solver for finite normal-form games (multi-agent strategic decision
making). Supports:
- Generic normal-form game solving (`solve_game`)
- Best-response computation (`best_response`)
- Canonical scenario analysis (`analyze_scenario`)
"""

from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, List, Sequence, Tuple

import logging
import math

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError, ModuleOperationError


logger = logging.getLogger(__name__)


Player = str
Strategy = str


@dataclass
class NormalFormGame:
    """Internal canonical representation of a finite normal-form game."""

    players: List[Player]
    strategies: Dict[Player, List[Strategy]]
    payoff_tensor: Any  # nested lists, dimension = len(players)


class GameTheorySolver(BaseBrainModule):
    """Game-theoretic reasoning module (normal-form games only, v1)."""

    MAX_PLAYERS = 5
    MAX_STRATEGIES_PER_PLAYER = 8
    MAX_PROFILES = 10_000

    def __init__(self) -> None:
        super().__init__()

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata for registry and routing."""
        return ModuleMetadata(
            name="game_theory_solver",
            version="0.1.0",
            description=(
                "Symbolic game-theoretic analysis for finite normal-form games "
                "(Nash equilibria, best responses, canonical scenarios)."
            ),
            operations=["solve_game", "analyze_scenario", "best_response"],
            dependencies=[],
            enabled=True,
            model_required=False,
        )

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch operations for the game theory solver.

        Supported operations:
        - solve_game: generic normal-form game solving
        - best_response: best responses for a player given others' strategies
        - analyze_scenario: canonical named scenarios (e.g., prisoners_dilemma)
        """
        logger.info(
            "GameTheorySolver.execute",
            extra={
                "module_name": self.metadata.name,
                "operation": operation,
                "params_keys": sorted(list(params.keys())),
            },
        )

        if operation == "solve_game":
            return self._solve_game(params)
        if operation == "best_response":
            return self._best_response(params)
        if operation == "analyze_scenario":
            return self._analyze_scenario(params)

        raise InvalidParameterError(
            "operation",
            operation,
            "Unknown operation for game_theory_solver",
        )

    # --- Core helpers: normalization and payoffs ---

    def _normalize_game(self, params: Dict[str, Any]) -> NormalFormGame:
        """
        Normalize raw params into a NormalFormGame.

        Expected params:
            players: list[str] or int
            strategies: dict[player, list[str]] or list[list[str]]
            payoffs: nested lists shaped (s1, ..., sn, n_players)
        """
        raw_players = params.get("players")
        raw_strategies = params.get("strategies")
        raw_payoffs = params.get("payoffs")

        if raw_players is None:
            raise InvalidParameterError("players", "missing", "players is required")

        if isinstance(raw_players, int):
            if raw_players <= 0:
                raise InvalidParameterError("players", str(raw_players), "must be > 0")
            players: List[Player] = [f"player_{i}" for i in range(raw_players)]
        elif isinstance(raw_players, list) and all(
            isinstance(p, str) for p in raw_players
        ):
            players = list(raw_players)
        else:
            raise InvalidParameterError(
                "players", str(raw_players), "must be int or list[str]"
            )

        n_players = len(players)
        if n_players == 0:
            raise InvalidParameterError("players", "[]", "at least one player required")
        if n_players > self.MAX_PLAYERS:
            raise InvalidParameterError(
                "players",
                str(n_players),
                f"too many players (max {self.MAX_PLAYERS})",
            )

        if raw_strategies is None:
            raise InvalidParameterError(
                "strategies", "missing", "strategies is required"
            )

        if isinstance(raw_strategies, dict):
            strategies: Dict[Player, List[Strategy]] = {}
            for p in players:
                s_list = raw_strategies.get(p)
                if not isinstance(s_list, list) or not s_list:
                    raise InvalidParameterError(
                        "strategies",
                        str(s_list),
                        f"strategies for player '{p}' must be non-empty list",
                    )
                strategies[p] = [str(s) for s in s_list]
        elif isinstance(raw_strategies, list):
            if len(raw_strategies) != n_players:
                raise InvalidParameterError(
                    "strategies",
                    str(raw_strategies),
                    "strategies list length must equal number of players",
                )
            strategies = {}
            for p, s_list in zip(players, raw_strategies):
                if not isinstance(s_list, list) or not s_list:
                    raise InvalidParameterError(
                        "strategies",
                        str(s_list),
                        f"strategies for player '{p}' must be non-empty list",
                    )
                strategies[p] = [str(s) for s in s_list]
        else:
            raise InvalidParameterError(
                "strategies",
                str(raw_strategies),
                "must be dict[player, list[str]] or list[list[str]]",
            )

        # Enforce per-player strategy caps
        for p, s_list in strategies.items():
            if len(s_list) > self.MAX_STRATEGIES_PER_PLAYER:
                raise InvalidParameterError(
                    "strategies",
                    f"{p}:{len(s_list)}",
                    f"too many strategies for player '{p}' "
                    f"(max {self.MAX_STRATEGIES_PER_PLAYER})",
                )

        if raw_payoffs is None:
            raise InvalidParameterError("payoffs", "missing", "payoffs is required")

        # Compute profile counts and guard combinatorial blowup
        profile_count = 1
        for p in players:
            profile_count *= len(strategies[p])
        if profile_count > self.MAX_PROFILES:
            raise InvalidParameterError(
                "payoffs",
                f"profiles={profile_count}",
                f"too many strategy profiles (max {self.MAX_PROFILES})",
            )

        # Basic numeric validation will occur when we index into payoffs
        return NormalFormGame(
            players=players,
            strategies=strategies,
            payoff_tensor=raw_payoffs,
        )

    def _get_payoff_profile(
        self,
        game: NormalFormGame,
        index_profile: Tuple[int, ...],
    ) -> List[float]:
        """
        Extract payoff vector for a profile of strategy indices.

        payoffs is expected as nested lists of shape
        (s1, s2, ..., sn, n_players).
        """
        node = game.payoff_tensor
        try:
            for idx in index_profile:
                node = node[idx]
            # Final dimension should be per-player payoffs
            if not isinstance(node, (list, tuple)):
                raise TypeError("final payoff node must be list/tuple")
            if len(node) != len(game.players):
                raise ValueError("payoff vector length must equal number of players")
            payoffs: List[float] = []
            for v in node:
                if not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v):
                    raise ValueError("payoffs must be finite numeric values")
                payoffs.append(float(v))
            return payoffs
        except Exception as exc:
            raise InvalidParameterError(
                "payoffs",
                "incompatible",
                f"payoffs shape does not match players/strategies: {exc}",
            ) from exc

    # --- Operations ---

    def _solve_game(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            game = self._normalize_game(params)
            mixed_requested = bool(params.get("mixed", False))
            equilibrium_type = str(params.get("equilibrium_type", "nash"))

            if equilibrium_type != "nash":
                raise InvalidParameterError(
                    "equilibrium_type",
                    equilibrium_type,
                    "only 'nash' equilibria are supported in v1",
                )

            equilibria: List[Dict[str, Any]] = []

            # Precompute strategy index mapping per player
            index_ranges: List[range] = [
                range(len(game.strategies[p])) for p in game.players
            ]

            total_profiles = 0
            for index_profile in product(*index_ranges):
                total_profiles += 1
                payoffs = self._get_payoff_profile(game, index_profile)

                # Check best-response condition for each player
                is_nash = True
                for player_idx, player in enumerate(game.players):
                    strategies_player = game.strategies[player]
                    current_idx = index_profile[player_idx]
                    current_payoff = payoffs[player_idx]

                    # Try unilateral deviations
                    for alt_idx in range(len(strategies_player)):
                        if alt_idx == current_idx:
                            continue
                        alt_profile = list(index_profile)
                        alt_profile[player_idx] = alt_idx
                        alt_payoffs = self._get_payoff_profile(
                            game, tuple(alt_profile)
                        )
                        if alt_payoffs[player_idx] > current_payoff:
                            is_nash = False
                            break

                    if not is_nash:
                        break

                if is_nash:
                    profile_strategies = {
                        player: game.strategies[player][idx]
                        for player, idx in zip(game.players, index_profile)
                    }
                    equilibria.append(
                        {
                            "type": "pure",
                            "strategies": profile_strategies,
                            "payoffs": {
                                player: payoffs[i]
                                for i, player in enumerate(game.players)
                            },
                        }
                    )

            mixed_status: str | None = None
            if mixed_requested:
                # Placeholder status; full mixed-strategy search is future work.
                mixed_status = "mixed_not_supported_v1"

            metadata: Dict[str, Any] = {
                "players": game.players,
                "strategy_counts": {
                    p: len(game.strategies[p]) for p in game.players
                },
                "total_profiles_checked": total_profiles,
                "equilibrium_type": "nash",
            }
            if mixed_status is not None:
                metadata["mixed_status"] = mixed_status

            logger.info(
                "GameTheorySolver.solve_game.complete",
                extra={
                    "module_name": self.metadata.name,
                    "players": game.players,
                    "strategy_counts": metadata["strategy_counts"],
                    "total_profiles_checked": total_profiles,
                    "equilibrium_count": len(equilibria),
                },
            )

            return {
                "success": True,
                "equilibria": equilibria,
                "metadata": metadata,
                "error": None,
            }
        except InvalidParameterError:
            raise
        except Exception as exc:
            logger.error(
                "GameTheorySolver.solve_game.error",
                exc_info=True,
                extra={
                    "module_name": self.metadata.name,
                    "operation": "solve_game",
                },
            )
            raise ModuleOperationError(
                module_name=self.metadata.name,
                operation="solve_game",
                reason=str(exc),
            ) from exc

    def _best_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            player = params.get("player")
            if not isinstance(player, str):
                raise InvalidParameterError(
                    "player",
                    str(player),
                    "player is required and must be a string",
                )

            fixed_profile = params.get("profile")
            if not isinstance(fixed_profile, dict):
                raise InvalidParameterError(
                    "profile",
                    str(fixed_profile),
                    "profile is required and must be a dict[player, strategy]",
                )

            game = self._normalize_game(params)

            if player not in game.players:
                raise InvalidParameterError(
                    "player",
                    player,
                    "player not present in game.players",
                )

            # Map fixed strategies to indices
            try:
                base_indices: List[int | None] = []
                for p in game.players:
                    if p == player:
                        base_indices.append(None)
                        continue
                    strategy_name = fixed_profile.get(p)
                    if strategy_name is None:
                        raise KeyError(
                            f"missing strategy for player '{p}' in profile"
                        )
                    try:
                        idx = game.strategies[p].index(strategy_name)
                    except ValueError as exc:
                        raise KeyError(
                            f"strategy '{strategy_name}' not in strategies for player '{p}'"
                        ) from exc
                    base_indices.append(idx)
            except Exception as exc:
                raise InvalidParameterError(
                    "profile",
                    str(fixed_profile),
                    f"invalid profile for players: {exc}",
                ) from exc

            # Enumerate candidate strategies for the target player
            player_idx = game.players.index(player)
            best_payoff = None
            best_responses: List[Strategy] = []
            payoffs_map: Dict[Strategy, float] = {}

            for s_idx, s_name in enumerate(game.strategies[player]):
                index_profile: List[int] = []
                for i, base_idx in enumerate(base_indices):
                    if i == player_idx:
                        index_profile.append(s_idx)
                    else:
                        assert base_idx is not None
                        index_profile.append(base_idx)

                payoff_vec = self._get_payoff_profile(game, tuple(index_profile))
                payoff = payoff_vec[player_idx]
                payoffs_map[s_name] = payoff
                if best_payoff is None or payoff > best_payoff:
                    best_payoff = payoff
                    best_responses = [s_name]
                elif payoff == best_payoff:
                    best_responses.append(s_name)

            logger.info(
                "GameTheorySolver.best_response.complete",
                extra={
                    "module_name": self.metadata.name,
                    "player": player,
                    "players": game.players,
                    "strategy_count": len(game.strategies[player]),
                    "best_response_count": len(best_responses),
                },
            )

            return {
                "success": True,
                "best_responses": best_responses,
                "payoffs": payoffs_map,
                "metadata": {
                    "player": player,
                    "players": game.players,
                },
                "error": None,
            }
        except InvalidParameterError:
            raise
        except Exception as exc:
            logger.error(
                "GameTheorySolver.best_response.error",
                exc_info=True,
                extra={
                    "module_name": self.metadata.name,
                    "operation": "best_response",
                },
            )
            raise ModuleOperationError(
                module_name=self.metadata.name,
                operation="best_response",
                reason=str(exc),
            ) from exc

    # --- Canonical scenarios ---

    def _get_scenario_spec(self, scenario: str) -> Dict[str, Any]:
        """Return raw game spec for a canonical scenario."""
        name = scenario.lower()

        if name == "prisoners_dilemma":
            # Players: A, B; Strategies: Cooperate (C), Defect (D)
            return {
                "players": ["A", "B"],
                "strategies": {
                    "A": ["C", "D"],
                    "B": ["C", "D"],
                },
                # Payoff ordering: (A, B)
                "payoffs": [
                    # A:C
                    [
                        [ -1, -1 ],  # B:C
                        [ -3,  0 ],  # B:D
                    ],
                    # A:D
                    [
                        [  0, -3 ],  # B:C
                        [ -2, -2 ],  # B:D
                    ],
                ],
            }

        if name == "stag_hunt":
            # Stag/Stag gives high payoff; Hare safer but lower.
            return {
                "players": ["A", "B"],
                "strategies": {
                    "A": ["Stag", "Hare"],
                    "B": ["Stag", "Hare"],
                },
                "payoffs": [
                    # A:Stag
                    [
                        [4, 4],  # B:Stag
                        [0, 3],  # B:Hare
                    ],
                    # A:Hare
                    [
                        [3, 0],  # B:Stag
                        [3, 3],  # B:Hare
                    ],
                ],
            }

        if name == "chicken":
            # Swerve / Straight chicken game.
            return {
                "players": ["A", "B"],
                "strategies": {
                    "A": ["Swerve", "Straight"],
                    "B": ["Swerve", "Straight"],
                },
                "payoffs": [
                    # A:Swerve
                    [
                        [0, 0],    # B:Swerve
                        [-1, 1],   # B:Straight
                    ],
                    # A:Straight
                    [
                        [1, -1],   # B:Swerve
                        [-10, -10] # B:Straight (crash)
                    ],
                ],
            }

        if name == "coordination":
            # Simple 2x2 coordination game with two pure NE.
            return {
                "players": ["A", "B"],
                "strategies": {
                    "A": ["X", "Y"],
                    "B": ["X", "Y"],
                },
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

        raise InvalidParameterError(
            "scenario",
            scenario,
            "unknown scenario; supported: prisoners_dilemma, stag_hunt, chicken, coordination",
        )

    def _analyze_scenario(self, params: Dict[str, Any]) -> Dict[str, Any]:
        scenario = params.get("scenario")
        if not isinstance(scenario, str) or not scenario:
            raise InvalidParameterError(
                "scenario",
                str(scenario),
                "scenario is required and must be a non-empty string",
            )

        try:
            try:
                base_spec = self._get_scenario_spec(scenario)
            except InvalidParameterError:
                raise
            except Exception as exc:
                raise ModuleOperationError(
                    module_name=self.metadata.name,
                    operation="analyze_scenario",
                    reason=f"failed to build scenario spec: {exc}",
                ) from exc

            # Allow overrides from params
            merged_params: Dict[str, Any] = {
                "players": base_spec["players"],
                "strategies": base_spec["strategies"],
                "payoffs": base_spec["payoffs"],
            }
            merged_params.update(
                {k: v for k, v in params.items() if k not in ("scenario",)}
            )

            result = self._solve_game(merged_params)

            analysis: Dict[str, Any] = {
                "dominant_strategies": {},
                "pareto_optimal_profiles": [],
            }

            # Dominant strategies: for each player, see if any strategy strictly
            # dominates all others in the equilibria found.
            equilibria = result.get("equilibria", [])
            for player in base_spec["players"]:
                payoff_by_strategy: Dict[Strategy, List[float]] = {}
                for eq in equilibria:
                    strategies = eq.get("strategies", {})
                    payoffs = eq.get("payoffs", {})
                    s = strategies.get(player)
                    if s is None:
                        continue
                    payoff_by_strategy.setdefault(s, []).append(
                        payoffs.get(player, 0.0)
                    )

                dominant: List[Strategy] = []
                for s_name, payoff_list in payoff_by_strategy.items():
                    if not payoff_list:
                        continue
                    avg_payoff = sum(payoff_list) / len(payoff_list)
                    strictly_better_than_all = True
                    for other_name, other_list in payoff_by_strategy.items():
                        if other_name == s_name or not other_list:
                            continue
                        other_avg = sum(other_list) / len(other_list)
                        if avg_payoff <= other_avg:
                            strictly_better_than_all = False
                            break
                    if strictly_better_than_all:
                        dominant.append(s_name)

                if dominant:
                    analysis["dominant_strategies"][player] = dominant

            # Pareto-optimal equilibria: no other equilibrium makes all players
            # at least as well off and one strictly better.
            for i, eq in enumerate(equilibria):
                pay_i = eq.get("payoffs", {})
                dominated = False
                for j, other in enumerate(equilibria):
                    if i == j:
                        continue
                    pay_j = other.get("payoffs", {})
                    all_ge = True
                    strictly_gt = False
                    for p in base_spec["players"]:
                        pi = pay_i.get(p, 0.0)
                        pj = pay_j.get(p, 0.0)
                        if pj < pi:
                            all_ge = False
                            break
                        if pj > pi:
                            strictly_gt = True
                    if all_ge and strictly_gt:
                        dominated = True
                        break
                if not dominated:
                    analysis["pareto_optimal_profiles"].append(eq)

            result["scenario"] = scenario
            result["analysis"] = analysis

            logger.info(
                "GameTheorySolver.analyze_scenario.complete",
                extra={
                    "module_name": self.metadata.name,
                    "scenario": scenario,
                    "equilibrium_count": len(equilibria),
                    "dominant_players": list(analysis["dominant_strategies"].keys()),
                },
            )

            return result
        except InvalidParameterError:
            raise
        except ModuleOperationError:
            raise
        except Exception as exc:
            logger.error(
                "GameTheorySolver.analyze_scenario.error",
                exc_info=True,
                extra={
                    "module_name": self.metadata.name,
                    "operation": "analyze_scenario",
                    "scenario": scenario,
                },
            )
            raise ModuleOperationError(
                module_name=self.metadata.name,
                operation="analyze_scenario",
                reason=str(exc),
            ) from exc

