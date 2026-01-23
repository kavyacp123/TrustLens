"""
Code Quality Agent
Metric-based quality assessment. Advisory only, non-blocking.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from schemas.agent_output import AgentOutput, AgentType, RiskLevel
from storage.s3_reader import S3Reader


class CodeQualityAgent(BaseAgent):
    """
    Evaluates code quality using metrics.
    NO LLM usage - purely metric-based.
    Advisory only - does not block.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.CODE_QUALITY, config)
        self.s3_reader = S3Reader()
        self.quality_thresholds = config.get("thresholds", {
            "max_function_length": 50,
            "max_file_length": 500,
            "min_comment_ratio": 0.1,
            "max_complexity": 10
        }) if config else {
            "max_function_length": 50,
            "max_file_length": 500,
            "min_comment_ratio": 0.1,
            "max_complexity": 10
        }
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        pass
    
    def analyze(self, s3_path: str, features: Dict[str, Any] = None) -> AgentOutput:
        """
        Analyze code quality.
        
        Args:
            s3_path: Path to code in S3
            features: Pre-extracted features
        
        Returns:
            AgentOutput with quality metrics
        """
        try:
            code_files = self.s3_reader.read_code_snapshot(s3_path)
            
            quality_metrics = self._calculate_quality_metrics(code_files, features)
            findings = self._generate_quality_findings(quality_metrics)
            
            # Quality is always advisory, confidence is high (metrics are deterministic)
            return self._create_output(
                confidence=0.9,
                findings=findings,
                risk_level=RiskLevel.LOW,  # Quality issues are low risk
                metadata={
                    "quality_metrics": quality_metrics,
                    "advisory": True,
                    "blocking": False
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
    
    def _calculate_quality_metrics(self, code_files: Dict[str, str], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate quality metrics.
        
        Args:
            code_files: Code files
            features: Pre-extracted features
        
        Returns:
            Quality metrics
        """
        metrics = {
            "total_loc": 0,
            "total_comments": 0,
            "comment_ratio": 0.0,
            "average_function_length": 0,
            "long_files": [],
            "long_functions": [],
            "complexity_score": 0
        }
        
        total_functions = 0
        total_function_lines = 0
        
        for filename, content in code_files.items():
            lines = content.split('\n')
            loc = len([l for l in lines if l.strip()])
            comments = len([l for l in lines if l.strip().startswith('#') or l.strip().startswith('//')])
            
            metrics["total_loc"] += loc
            metrics["total_comments"] += comments
            
            # Check file length
            if loc > self.quality_thresholds["max_file_length"]:
                metrics["long_files"].append({"file": filename, "loc": loc})
            
            # Estimate function lengths (placeholder logic)
            function_count = content.count('def ') + content.count('function ')
            if function_count > 0:
                total_functions += function_count
                total_function_lines += loc
        
        # Calculate ratios
        if metrics["total_loc"] > 0:
            metrics["comment_ratio"] = metrics["total_comments"] / metrics["total_loc"]
        
        if total_functions > 0:
            metrics["average_function_length"] = total_function_lines / total_functions
        
        # Use features for complexity
        if features and "complexity_indicators" in features.get("features", {}):
            metrics["complexity_score"] = features["features"]["complexity_indicators"].get("nested_depth", 0)
        
        return metrics
    
    def _generate_quality_findings(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate quality findings from metrics.
        
        Args:
            metrics: Calculated metrics
        
        Returns:
            List of findings
        """
        findings = []
        
        # Check comment ratio
        if metrics["comment_ratio"] < self.quality_thresholds["min_comment_ratio"]:
            findings.append({
                "type": "low_documentation",
                "severity": "info",
                "description": f"Comment ratio {metrics['comment_ratio']:.2f} below threshold {self.quality_thresholds['min_comment_ratio']}"
            })
        
        # Check file lengths
        for long_file in metrics["long_files"]:
            findings.append({
                "type": "long_file",
                "severity": "info",
                "description": f"File {long_file['file']} has {long_file['loc']} lines"
            })
        
        # Check average function length
        if metrics["average_function_length"] > self.quality_thresholds["max_function_length"]:
            findings.append({
                "type": "long_functions",
                "severity": "info",
                "description": f"Average function length {metrics['average_function_length']:.1f} exceeds threshold"
            })
        
        # Check complexity
        if metrics["complexity_score"] > self.quality_thresholds["max_complexity"]:
            findings.append({
                "type": "high_complexity",
                "severity": "warning",
                "description": f"Code complexity score {metrics['complexity_score']} is high"
            })
        
        return findings
