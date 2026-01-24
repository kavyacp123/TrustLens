"""
Reliability Engine
Tracks agent reliability, confidence aggregation, and failure handling.
"""

from typing import List, Dict, Any
from schemas.agent_output import AgentOutput
import statistics


class ReliabilityEngine:
    """
    Manages reliability tracking and confidence aggregation.
    """
    
    def __init__(self):
        self.agent_history: Dict[str, List[float]] = {}
    
    def aggregate_confidence(self, outputs: List[AgentOutput]) -> float:
        """
        Aggregate confidence from multiple agent outputs.
        
        Args:
            outputs: List of agent outputs
        
        Returns:
            Aggregated confidence score (0.0-1.0)
        """
        if not outputs:
            return 0.0
        
        successful_outputs = [o for o in outputs if o.success]
        
        if not successful_outputs:
            return 0.0
        
        confidences = [o.confidence for o in successful_outputs]
        
        # Use weighted mean based on agent reliability
        weighted_confidences = []
        for output in successful_outputs:
            agent_name = output.agent_type.value
            reliability = self._get_agent_reliability(agent_name)
            weighted_confidences.append(output.confidence * reliability)
        
        if weighted_confidences:
            return sum(weighted_confidences) / len(weighted_confidences)
        else:
            return statistics.mean(confidences)
    
    def _get_agent_reliability(self, agent_name: str) -> float:
        """
        Get historical reliability of an agent.
        
        Args:
            agent_name: Name of agent
        
        Returns:
            Reliability score (0.0-1.0)
        """
        if agent_name not in self.agent_history:
            return 1.0  # Default reliability for new agents
        
        history = self.agent_history[agent_name]
        if not history:
            return 1.0
        
        # Calculate reliability from historical performance
        return statistics.mean(history)
    
    def record_agent_performance(self, agent_name: str, confidence: float):
        """
        Record agent performance for future reliability calculations.
        
        Args:
            agent_name: Name of agent
            confidence: Confidence achieved
        """
        if agent_name not in self.agent_history:
            self.agent_history[agent_name] = []
        
        self.agent_history[agent_name].append(confidence)
        
        # Keep only recent history (last 100 runs)
        if len(self.agent_history[agent_name]) > 100:
            self.agent_history[agent_name] = self.agent_history[agent_name][-100:]
    
    def should_defer(
        self,
        overall_confidence: float,
        conflicts: List[Dict[str, Any]],
        min_confidence_threshold: float = 0.7
    ) -> tuple[bool, str]:
        """
        Determine if system should defer decision.
        
        Args:
            overall_confidence: Aggregated confidence
            conflicts: Detected conflicts
            min_confidence_threshold: Minimum acceptable confidence
        
        Returns:
            Tuple of (should_defer, reason)
        """
        # Defer if confidence is too low
        if overall_confidence < min_confidence_threshold:
            return True, f"Overall confidence {overall_confidence:.2f} below threshold {min_confidence_threshold}"
        
        # Defer if there are unresolved conflicts
        if conflicts:
            return True, f"{len(conflicts)} unresolved conflicts between agents"
        
        return False, ""
    
    def calculate_system_health(self, outputs: List[AgentOutput]) -> Dict[str, Any]:
        """
        Calculate overall system health metrics.
        
        Args:
            outputs: All agent outputs
        
        Returns:
            Health metrics
        """
        total = len(outputs)
        successful = len([o for o in outputs if o.success])
        failed = total - successful
        
        avg_confidence = self.aggregate_confidence(outputs)
        
        return {
            "total_agents": total,
            "successful_agents": successful,
            "failed_agents": failed,
            "success_rate": successful / total if total > 0 else 0.0,
            "average_confidence": avg_confidence,
            "health_status": "healthy" if successful == total and avg_confidence > 0.7 else "degraded"
        }
