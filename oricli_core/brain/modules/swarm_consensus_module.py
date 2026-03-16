from __future__ import annotations
"""
Swarm Consensus Module
Builds consensus from distributed node contributions and peer reviews.
"""

from collections import Counter
from typing import Any, Dict, List

from oricli_core.brain.base_module import BaseBrainModule, ModuleMetadata
from oricli_core.exceptions import InvalidParameterError


class SwarmConsensusModule(BaseBrainModule):
    """Module for building consensus in swarm intelligence."""

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="swarm_consensus",
            version="1.1.0",
            description="Builds consensus from distributed agent contributions and reviews",
            operations=["status", "evaluate_consensus"],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "status":
            return {"success": True, "status": "active"}
        if operation == "evaluate_consensus":
            return self._evaluate_consensus(params)
        return {"success": False, "error": f"Unknown operation: {operation}"}

    def _score_contribution(self, contribution: Dict[str, Any], reviews: List[Dict[str, Any]]) -> float:
        score = 1.0 if contribution.get("success") else -1.0
        if contribution.get("contribution"):
            score += min(len(str(contribution["contribution"])) / 160.0, 1.0)

        for review in reviews:
            confidence = float(review.get("confidence", 0.0))
            if review.get("approval"):
                score += 1.0 + confidence
            else:
                score -= 0.75 + confidence
                score -= 0.15 * len(review.get("issues", []))
        return score

    def _majority_score(self, reviews: List[Dict[str, Any]]) -> tuple[int, float]:
        approvals = sum(1 for review in reviews if review.get("approval"))
        rejections = sum(1 for review in reviews if not review.get("approval"))
        confidence_sum = sum(float(review.get("confidence", 0.0)) for review in reviews)
        return approvals - rejections, confidence_sum

    def _select_ranked_entry(
        self,
        ranked: List[Dict[str, Any]],
        *,
        policy: str,
        verifier_agent_types: List[str],
    ) -> Dict[str, Any]:
        if policy == "majority":
            return max(
                ranked,
                key=lambda item: (
                    self._majority_score(item["reviews"])[0],
                    self._majority_score(item["reviews"])[1],
                    item["score"],
                ),
            )
        if policy == "verifier_wins":
            verifier_approved = [
                item
                for item in ranked
                if any(
                    review.get("approval")
                    and str(review.get("reviewer_agent_type") or "") in verifier_agent_types
                    for review in item["reviews"]
                )
            ]
            if verifier_approved:
                verifier_approved.sort(key=lambda item: item["score"], reverse=True)
                return verifier_approved[0]
        return ranked[0]

    def _build_final_answer(self, ranked: List[Dict[str, Any]], policy: str) -> str:
        if not ranked:
            return ""
        if policy == "merge_top" and len(ranked) > 1:
            top_entries = [entry["contribution"].get("contribution", "").strip() for entry in ranked[:2]]
            merged = "\n\n".join(text for text in top_entries if text)
            return merged.strip()
        return str(ranked[0]["contribution"].get("contribution", "")).strip()

    def _build_dissent_report(self, ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dissent_report: List[Dict[str, Any]] = []
        for item in ranked:
            dissenting_reviews = [review for review in item["reviews"] if not review.get("approval")]
            if not dissenting_reviews:
                continue
            issue_counter: Counter[str] = Counter()
            for review in dissenting_reviews:
                issue_counter.update(str(issue) for issue in review.get("issues", []))
            dissent_report.append(
                {
                    "node_id": item["node_id"],
                    "agent_type": item["agent_type"],
                    "reviewer_count": len(dissenting_reviews),
                    "issues": [
                        {"issue": issue, "count": count}
                        for issue, count in issue_counter.most_common()
                    ],
                    "summaries": [review.get("summary") for review in dissenting_reviews if review.get("summary")],
                }
            )
        return dissent_report

    def _evaluate_consensus(self, params: Dict[str, Any]) -> Dict[str, Any]:
        contributions = list(params.get("contributions") or [])
        reviews = list(params.get("reviews") or [])
        if not contributions:
            raise InvalidParameterError("contributions", contributions, "At least one contribution is required")

        ranked: List[Dict[str, Any]] = []
        for contribution in contributions:
            node_reviews = [
                review
                for review in reviews
                if review.get("target_node_id") == contribution.get("node_id")
            ]
            ranked.append(
                {
                    "node_id": contribution.get("node_id"),
                    "agent_type": contribution.get("agent_type"),
                    "contribution": contribution,
                    "reviews": node_reviews,
                    "score": self._score_contribution(contribution, node_reviews),
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        policy = str(params.get("consensus_policy") or "weighted_vote")
        verifier_agent_types = [
            str(agent_type)
            for agent_type in (params.get("verifier_agent_types") or ["verifier", "analysis"])
        ]
        best = self._select_ranked_entry(
            ranked,
            policy=policy,
            verifier_agent_types=verifier_agent_types,
        )
        final_answer = self._build_final_answer(
            [best] + [item for item in ranked if item["node_id"] != best["node_id"]],
            policy,
        )
        dissenting_points = [
            issue_entry["issue"]
            for item in self._build_dissent_report(ranked)
            for issue_entry in item["issues"]
        ]
        consensus_level = "high" if best["score"] >= 2.5 else "medium" if best["score"] >= 1.0 else "low"
        conflicts_detected = any(not review.get("approval") for review in reviews)
        arbitration_summary = (
            f"Selected {best['node_id']} via {policy} policy."
            if not conflicts_detected
            else f"Selected {best['node_id']} via {policy} after reviewing dissent."
        )

        return {
            "success": bool(best["contribution"].get("success")) and bool(final_answer),
            "answer": final_answer,
            "selected_node_id": best["node_id"],
            "selected_agent_type": best["agent_type"],
            "consensus_level": consensus_level,
            "policy": policy,
            "verifier_agent_types": verifier_agent_types,
            "conflicts_detected": conflicts_detected,
            "arbitration_summary": arbitration_summary,
            "ranked_contributions": ranked,
            "dissenting_points": dissenting_points,
            "dissent_report": self._build_dissent_report(ranked),
        }
