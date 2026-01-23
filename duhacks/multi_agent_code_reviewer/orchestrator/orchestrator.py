"""
Orchestrator
Coordinates all agents and manages the analysis workflow.
"""

from typing import Dict, Any, List
from datetime import datetime
from schemas.agent_output import AgentOutput, AgentType
from schemas.final_report import FinalReport, RiskLevel
from agents.feature_agent import FeatureExtractionAgent
from agents.security_agent import SecurityAnalysisAgent
from agents.logic_agent import LogicAnalysisAgent
from agents.code_quality_agent import CodeQualityAgent
from agents.decision_agent import DecisionAgent
from .conflict_resolver import ConflictResolver
from .reliability import ReliabilityEngine
from utils.logger import Logger


class Orchestrator:
    """
    Coordinates all agents and manages the analysis workflow.
    Routes tasks, aggregates results, handles conflicts.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize orchestrator with all agents."""
        self.config = config or {}
        self.logger = Logger("Orchestrator")
        
        # Initialize agents
        self.feature_agent = FeatureExtractionAgent()
        self.security_agent = SecurityAnalysisAgent(config.get("security_config"))
        self.logic_agent = LogicAnalysisAgent(config.get("logic_config"))
        self.quality_agent = CodeQualityAgent(config.get("quality_config"))
        self.decision_agent = DecisionAgent(config.get("decision_config"))
        
        # Initialize support systems
        self.conflict_resolver = ConflictResolver()
        self.reliability_engine = ReliabilityEngine()
    
    def analyze_repository(self, repo_url: str, s3_path: str) -> FinalReport:
        """Analyze a code repository."""
        self.logger.info(f"Starting analysis for {repo_url}")
        
        # Step 1: Feature Extraction
        feature_output = self.feature_agent.analyze(s3_path)
        if not feature_output.success:
            return self._create_error_report(repo_url, s3_path, "Feature extraction failed", feature_output.error_message)
        
        features = feature_output.metadata.get("features", {})
        
        # Step 2: Run analysis agents
        agent_outputs = self._run_analysis_agents(s3_path, features)
        all_outputs = [feature_output] + agent_outputs
        
        # Step 3: Detect conflicts
        conflicts = self.conflict_resolver.detect_conflicts(agent_outputs)
        
        # Step 4: Aggregate confidence
        overall_confidence = self.reliability_engine.aggregate_confidence(agent_outputs)
        
        # Step 5: Check deferral
        should_defer, defer_reason = self.reliability_engine.should_defer(overall_confidence, conflicts)
        
        # Step 6: Get decision
        decision_output = self.decision_agent.recommend_action(agent_outputs, overall_confidence, conflicts)
        all_outputs.append(decision_output)
        
        # Step 7: Generate report
        risk_levels = [o.risk_level for o in agent_outputs if o.success]
        overall_risk = max(risk_levels) if risk_levels else RiskLevel.NONE
        
        report = FinalReport(
            repository_url=repo_url,
            s3_snapshot_path=s3_path,
            timestamp=datetime.now(),
            overall_confidence=overall_confidence,
            overall_risk_level=overall_risk,
            agent_outputs=all_outputs,
            conflicts=conflicts,
            recommendation=decision_output.metadata.get("recommendation", "unknown"),
            action_recommended=decision_output.metadata.get("recommendation"),
            deferred=should_defer,
            deferral_reason=defer_reason if should_defer else None,
            metadata={"system_health": self.reliability_engine.calculate_system_health(all_outputs)}
        )
        
        return report
    
    def _run_analysis_agents(self, s3_path: str, features: Dict[str, Any]) -> List[AgentOutput]:
        """Run all analysis agents."""
        outputs = []
        
        try:
            outputs.append(self.security_agent.analyze(s3_path, features))
        except Exception as e:
            self.logger.error(f"Security agent failed: {e}")
        
        try:
            outputs.append(self.logic_agent.analyze(s3_path, features))
        except Exception as e:
            self.logger.error(f"Logic agent failed: {e}")
        
        try:
            outputs.append(self.quality_agent.analyze(s3_path, features))
        except Exception as e:
            self.logger.error(f"Quality agent failed: {e}")
        
        return outputs
    
    def _create_error_report(self, repo_url: str, s3_path: str, error_type: str, error_message: str) -> FinalReport:
        """Create error report when analysis fails."""
        return FinalReport(
            repository_url=repo_url,
            s3_snapshot_path=s3_path,
            timestamp=datetime.now(),
            overall_confidence=0.0,
            overall_risk_level=RiskLevel.NONE,
            agent_outputs=[],
            conflicts=[],
            recommendation="Analysis failed",
            action_recommended="defer",
            deferred=True,
            deferral_reason=f"{error_type}: {error_message}",
            metadata={"error": True}
        )
