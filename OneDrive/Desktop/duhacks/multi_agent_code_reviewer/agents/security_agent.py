"""
Security Analysis Agent
Analyzes code for security risks using Gemini LLM.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from schemas.agent_output import AgentOutput, AgentType, RiskLevel
from storage.s3_reader import S3Reader
from llm.gemini_client import GeminiClient


class SecurityAnalysisAgent(BaseAgent):
    """
    Detects security vulnerabilities using LLM.
    Uses bounded prompts and limited code snippets.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.SECURITY_ANALYSIS, config)
        self.s3_reader = S3Reader()
        self.gemini_client = GeminiClient()
        self.max_snippet_length = config.get("max_snippet_length", 500) if config else 500
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        if self.config.get("max_snippet_length", 500) < 100:
            raise ValueError("max_snippet_length must be at least 100")
    
    def analyze(self, s3_path: str, features: Dict[str, Any] = None) -> AgentOutput:
        """
        Analyze code for security risks.
        
        Args:
            s3_path: Path to code snapshot in S3
            features: Pre-extracted features from FeatureExtractionAgent
        
        Returns:
            AgentOutput with security findings
        """
        try:
            # Read code from S3
            code_files = self.s3_reader.read_code_snapshot(s3_path)
            
            # Identify high-risk files based on features
            risk_files = self._identify_risk_files(code_files, features)
            
            # Analyze with LLM (bounded)
            findings = []
            total_confidence = 0.0
            
            for filename, content in risk_files.items():
                snippet = self._extract_snippet(content)
                result = self._analyze_snippet_with_llm(filename, snippet)
                findings.extend(result["findings"])
                total_confidence += result["confidence"]
            
            # Calculate overall confidence
            avg_confidence = total_confidence / len(risk_files) if risk_files else 0.5
            
            # Determine risk level
            risk_level = self._determine_risk_level(findings)
            
            return self._create_output(
                confidence=avg_confidence,
                findings=findings,
                risk_level=risk_level,
                metadata={
                    "files_analyzed": len(risk_files),
                    "total_files": len(code_files),
                    "s3_path": s3_path
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
    
    def _identify_risk_files(self, code_files: Dict[str, str], features: Dict[str, Any]) -> Dict[str, str]:
        """
        Identify files that need security review.
        
        Args:
            code_files: All code files
            features: Extracted features
        
        Returns:
            Dictionary of high-risk files
        """
        risk_keywords = ['auth', 'login', 'password', 'token', 'crypto', 'sql', 'exec', 'eval']
        risk_files = {}
        
        for filename, content in code_files.items():
            if any(keyword in filename.lower() or keyword in content.lower() for keyword in risk_keywords):
                risk_files[filename] = content
        
        return risk_files
    
    def _extract_snippet(self, content: str) -> str:
        """
        Extract relevant code snippet for LLM analysis.
        
        Args:
            content: Full file content
        
        Returns:
            Truncated snippet
        """
        # Simple truncation - in production, use smarter extraction
        return content[:self.max_snippet_length]
    
    def _analyze_snippet_with_llm(self, filename: str, snippet: str) -> Dict[str, Any]:
        """
        Analyze code snippet using Gemini LLM.
        
        Args:
            filename: Name of file
            snippet: Code snippet
        
        Returns:
            Dictionary with findings and confidence
        """
        prompt = f"""
        Analyze this code snippet for SECURITY RISKS ONLY.
        File: {filename}
        
        Code:
        {snippet}
        
        Identify:
        1. SQL injection risks
        2. Authentication/authorization issues
        3. Input validation gaps
        4. Cryptographic weaknesses
        5. Code execution vulnerabilities
        
        Return JSON format:
        {{
            "findings": [
                {{"type": "...", "severity": "...", "description": "...", "line": "..."}}
            ],
            "confidence": 0.0-1.0
        }}
        """
        
        # Call LLM (mocked for skeleton)
        llm_response = self.gemini_client.generate(prompt)
        
        # Parse response (placeholder)
        return {
            "findings": llm_response.get("findings", []),
            "confidence": llm_response.get("confidence", 0.7)
        }
    
    def _determine_risk_level(self, findings: List[Dict[str, Any]]) -> RiskLevel:
        """
        Determine overall risk level from findings.
        
        Args:
            findings: List of security findings
        
        Returns:
            RiskLevel enum
        """
        if not findings:
            return RiskLevel.NONE
        
        severities = [f.get("severity", "low") for f in findings]
        
        if "critical" in severities:
            return RiskLevel.CRITICAL
        elif "high" in severities:
            return RiskLevel.HIGH
        elif "medium" in severities:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
