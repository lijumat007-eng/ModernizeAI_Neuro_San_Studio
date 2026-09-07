# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tier 5: Transformation Memory Engine.
Stores modernization metrics, 6R classifications, complexity scores, and target microservice schemas.
"""

from typing import Any, Dict, List, Optional


class TransformationMemory:
    """
    Tier 5 Transformation Memory tracking modernization roadmap data and architectural scores.
    """

    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.recommendations: Dict[str, Dict[str, Any]] = {}
        self.candidate_microservices: List[Dict[str, Any]] = []

    def record_metrics(
        self,
        component_name: str,
        afferent_coupling: int,
        efferent_coupling: int,
        cyclomatic_complexity: int,
        lines_of_code: int,
    ):
        total_coupling = afferent_coupling + efferent_coupling
        instability = (efferent_coupling / total_coupling) if total_coupling > 0 else 0.0
        self.metrics[component_name] = {
            "component": component_name,
            "afferent_coupling": afferent_coupling,
            "efferent_coupling": efferent_coupling,
            "instability": round(instability, 3),
            "cyclomatic_complexity": cyclomatic_complexity,
            "lines_of_code": lines_of_code,
        }

    def record_recommendation(
        self,
        component_name: str,
        strategy_6r: str,
        target_pattern: str,
        priority: str,
        rationale: str,
        risks: List[str],
    ):
        self.recommendations[component_name] = {
            "component": component_name,
            "strategy_6r": strategy_6r, # Rehost, Replatform, Refactor, Retire, Repurchase, Retain
            "target_pattern": target_pattern, # e.g. Event-Driven Microservice, Serverless Function, ACL
            "priority": priority, # High, Medium, Low, Phase 1, Phase 2
            "rationale": rationale,
            "risks": risks,
        }

    def register_candidate_microservice(
        self,
        domain_name: str,
        components: List[str],
        tables: List[str],
        business_rules: List[str],
        rationale: str,
    ):
        self.candidate_microservices.append({
            "domain_name": domain_name,
            "components": components,
            "tables": tables,
            "business_rules": business_rules,
            "rationale": rationale,
        })

    def get_component_scorecard(self, component_name: str) -> Optional[Dict[str, Any]]:
        metric = self.metrics.get(component_name, {})
        rec = self.recommendations.get(component_name, {})
        if not metric and not rec:
            return None
        return {**metric, **rec}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics,
            "recommendations": self.recommendations,
            "candidate_microservices": self.candidate_microservices,
        }
