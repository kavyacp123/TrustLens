"""
Decision Agent
Recommends actions based on all agent outputs.
NEVER makes final decisions - only recommendations.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from schemas.agent_output import AgentOutput, AgentType, RiskLevel


class DecisionAgent(BaseAgent):
    """
    Synthesizes all agent outputs and recommends action.
    Does NOT make final decisions.
    Does NOT execute any actions.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.DECISION, config)
        self.min_confidence_threshold = config.get("min_confidence", 0.7) if config else 0.7
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        pass
    
    def analyze(self, s3_path: str, features: Dict[str, Any] = None) -> AgentOutput:
        """
        Not used for decision agent.
        Decision agent uses recommend_action() instead.
        """
        raise NotImplementedError("DecisionAgent uses recommend_action(), not analyze()")
    
    def recommend_action(
        self,
        all_outputs: List[AgentOutput],
        overall_confidence: float,
        conflicts: List[Dict[str, Any]]
    ) -> AgentOutput:
        """
        Recommend action based on all agent outputs.
        
        Args:
            all_outputs: Outputs from all other agents
            overall_confidence: Aggregated confidence
            conflicts: Detected conflicts
        
        Returns:
            AgentOutput with recommendation
        """
        try:
            # Collect risk levels
            risk_levels = [output.risk_level for output in all_outputs if output.success]
            
            # Determine recommendation
            recommendation = self._determine_recommendation(
                risk_levels,
                overall_confidence,
                conflicts
            )
            
            # Calculate decision confidence
            decision_confidence = self._calculate_decision_confidence(
                overall_confidence,
                len(conflicts)
            )
            
            findings = [{
                "recommendation": recommendation["action"],
                "reasoning": recommendation["reasoning"],
                "defer_if_needed": recommendation["defer"]
            }]
            
            return self._create_output(
                confidence=decision_confidence,
                findings=findings,
                risk_level=max(risk_levels) if risk_levels else RiskLevel.NONE,
                metadata={
                    "recommendation": recommendation["action"],
                    "defer": recommendation["defer"],
                    "conflicts_present": len(conflicts) > 0
                }
            )
        except Exception as e:
            return self._create_output(
                confidence=0.0,
                findings=[],
                risk_level=RiskLevel.NONE,
                metadata={},
                success=False,
                error_message=str(e)
            )
    
    def _determine_recommendation(
        self,
        risk_levels: List[RiskLevel],
        confidence: float,
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Determine recommended action.
        
        Args:
            risk_levels: All risk levels from agents
            confidence: Overall confidence
            conflicts: Conflicts detected
        
        Returns:
            Recommendation dictionary
        """
        # DEFER if confidence is too low
        if confidence < self.min_confidence_threshold:
            return {
                "action": "defer",
                "reasoning": f"Confidence {confidence:.2f} below threshold {self.min_confidence_threshold}",
                "defer": True
            }
        
        # DEFER if there are unresolved conflicts
        if conflicts:
            return {
                "action": "defer",
                "reasoning": f"Unresolved conflicts detected between agents: {len(conflicts)} conflicts",
                "defer": True
            }
        
        # Check highest risk level
        if RiskLevel.CRITICAL in risk_levels:
            return {
                "action": "manual_review_required",
                "reasoning": "Critical security or logic issues detected",
                "defer": False
            }
        
        if RiskLevel.HIGH in risk_levels:
            return {
                "action": "review_required",
                "reasoning": "High-severity issues found",
                "defer": False
            }
        
        if RiskLevel.MEDIUM in risk_levels:
            return {
                "action": "proceed_with_caution",
                "reasoning": "Medium-severity issues detected, proceed with awareness",
                "defer": False
            }
        
        # Low or no risk
        return {
            "action": "acceptable",
            "reasoning": "No significant issues detected",
            "defer": False
        }
    
    def _calculate_decision_confidence(self, overall_confidence: float, conflict_count: int) -> float:
        """
        Calculate confidence in the decision itself.
        
        Args:
            overall_confidence: Aggregated confidence from agents
            conflict_count: Number of conflicts
        
        Returns:
            Decision confidence
        """
        # Reduce confidence based on conflicts
        penalty = min(0.2 * conflict_count, 0.5)
        return max(overall_confidence - penalty, 0.0)
