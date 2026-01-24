"""
Logic Analysis Agent
Analyzes code logic and correctness using Gemini LLM.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from schemas.agent_output import AgentOutput, AgentType, RiskLevel
from storage.s3_reader import S3Reader
from llm.gemini_client import GeminiClient


class LogicAnalysisAgent(BaseAgent):
    """
    Analyzes code logic for correctness.
    Uses LLM for logic validation only.
    Does NOT check security or quality.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.LOGIC_ANALYSIS, config)
        self.s3_reader = S3Reader()
        self.gemini_client = GeminiClient()
        self.max_snippet_length = config.get("max_snippet_length", 600) if config else 600
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        pass
    
    def analyze(self, s3_path: str, features: Dict[str, Any] = None) -> AgentOutput:
        """
        Analyze code logic.
        
        Args:
            s3_path: Path to code snapshot in S3
            features: Pre-extracted features
        
        Returns:
            AgentOutput with logic analysis
        """
        try:
            # Read code from S3
            code_files = self.s3_reader.read_code_snapshot(s3_path)
            
            # Identify complex logic files
            logic_files = self._identify_logic_files(code_files, features)
            
            # Analyze with LLM
            findings = []
            total_confidence = 0.0
            
            for filename, content in logic_files.items():
                snippet = content[:self.max_snippet_length]
                result = self._analyze_logic_with_llm(filename, snippet, features)
                findings.extend(result["findings"])
                total_confidence += result["confidence"]
            
            avg_confidence = total_confidence / len(logic_files) if logic_files else 0.6
            
            # Logic issues map to risk levels
            risk_level = self._determine_risk_from_logic(findings)
            
            return self._create_output(
                confidence=avg_confidence,
                findings=findings,
                risk_level=risk_level,
                metadata={
                    "files_analyzed": len(logic_files),
                    "total_files": len(code_files)
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
    
    def _identify_logic_files(self, code_files: Dict[str, str], features: Dict[str, Any]) -> Dict[str, str]:
        """
        Identify files with complex logic.
        
        Args:
            code_files: All code files
            features: Extracted features
        
        Returns:
            Files requiring logic analysis
        """
        complex_files = {}
        
        # Use features to identify complex files
        if features and "complexity_indicators" in features.get("features", {}):
            complexity = features["features"]["complexity_indicators"]
            threshold = 3  # nesting depth threshold
            
            for filename, content in code_files.items():
                # Check for control flow keywords
                if ('if ' in content or 'for ' in content or 'while ' in content):
                    complex_files[filename] = content
        else:
            # Fallback: analyze all files
            complex_files = code_files
        
        return complex_files
    
    def _analyze_logic_with_llm(self, filename: str, snippet: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze logic using LLM.
        
        Args:
            filename: File name
            snippet: Code snippet
            features: Context features
        
        Returns:
            Analysis results
        """
        prompt = f"""
        Analyze this code for LOGIC CORRECTNESS ONLY.
        File: {filename}
        
        Code:
        {snippet}
        
        Check for:
        1. Infinite loops
        2. Unreachable code
        3. Logic contradictions
        4. Off-by-one errors
        5. Incorrect conditionals
        6. Missing edge case handling
        
        Do NOT check security or code quality.
        
        Return JSON:
        {{
            "findings": [
                {{"issue": "...", "severity": "...", "description": "..."}}
            ],
            "confidence": 0.0-1.0
        }}
        """
        
        llm_response = self.gemini_client.generate(prompt)
        
        return {
            "findings": llm_response.get("findings", []),
            "confidence": llm_response.get("confidence", 0.6)
        }
    
    def _determine_risk_from_logic(self, findings: List[Dict[str, Any]]) -> RiskLevel:
        """
        Map logic issues to risk levels.
        
        Args:
            findings: Logic findings
        
        Returns:
            Risk level
        """
        if not findings:
            return RiskLevel.NONE
        
        critical_issues = ["infinite_loop", "logic_contradiction"]
        high_issues = ["unreachable_code", "off_by_one"]
        
        for finding in findings:
            issue_type = finding.get("issue", "").lower()
            if any(critical in issue_type for critical in critical_issues):
                return RiskLevel.HIGH
            if any(high in issue_type for high in high_issues):
                return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
