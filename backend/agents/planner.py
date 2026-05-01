"""
Planner agent for ELYSIUM.

Responsible for deciding:
- what actions to take
- in what order
- with what parameters

This is a deterministic, rule-based planner for now.
Later, this can be upgraded to LLM-based planning.
"""

from typing import Dict, List


class DiscoveryPlanner:
    """
    Produces a structured plan for drug discovery
    given a target and constraints.
    """

    def __init__(
        self,
        target_id: str,
        num_molecules: int = 10,
        lipinski_only: bool = True,
    ):
        self.target_id = target_id
        self.num_molecules = num_molecules
        self.lipinski_only = lipinski_only

    def build_plan(self) -> List[Dict]:
        """
        Returns an ordered list of actions the agent should execute.
        """

        plan = []

        # Step 1: Generate molecules
        plan.append({
            "action": "generate_molecules",
            "params": {
                "target_id": self.target_id,
                "num_molecules": self.num_molecules,
            },
        })

        # Step 2: Score molecules
        plan.append({
            "action": "score_molecules",
            "params": {
                "lipinski_only": self.lipinski_only,
            },
        })

        # Step 3: Rank molecules
        plan.append({
            "action": "rank_molecules",
            "params": {
                "strategy": "binding_affinity",
            },
        })

        # Step 4: Persist results
        plan.append({
            "action": "store_results",
            "params": {},
        })

        return plan


def create_discovery_plan(
    target_id: str,
    num_molecules: int = 10,
    lipinski_only: bool = True,
) -> List[Dict]:
    """
    Convenience function used by discovery_agent.
    """

    planner = DiscoveryPlanner(
        target_id=target_id,
        num_molecules=num_molecules,
        lipinski_only=lipinski_only,
    )

    return planner.build_plan()
