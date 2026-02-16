"""
Gemini LLM Client
Wrapper for Google Gemini API calls.
Supports real Gemini API with smart fallback analysis.
"""

from typing import Dict, Any
import json
import re


class GeminiClient:
    """
    Client for interacting with Google Gemini LLM.
    Used ONLY by agents, NEVER by orchestrator.
    
    When the real API is unavailable (no key, quota exhausted, etc.),
    falls back to snippet-aware static analysis that generates
    contextually correct findings based on actual code patterns.
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini client.
        """
        import os
        from utils.logger import Logger
        self.logger = Logger("GeminiClient")
        
        # Load API key, prioritizing explicit arg then env vars (case-insensitive)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            self.api_key = os.environ.get("gemini_api_key")
            
        if not self.api_key:
            self.logger.warning("⚠️ GEMINI_API_KEY not found in environment variables - Using FALLBACK analysis mode")
            self.api_key = "PLACEHOLDER_API_KEY"
        else:
            masked = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "****"
            self.logger.info(f"✅ Gemini API key loaded (Key: {masked})")

        self.model_name = model
        
        try:
            import google.generativeai as genai
            if self.api_key != "PLACEHOLDER_API_KEY":
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(model)
                self.client_ready = True
                self.logger.info(f"✅ Gemini model initialized: {model}")
            else:
                self.model = None
                self.client_ready = False
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Gemini API: {e}")
            self.model = None
            self.client_ready = False
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Generate response from Gemini.
        Falls back to snippet-aware analysis if API call fails.
        """
        if self.client_ready and self.api_key != "PLACEHOLDER_API_KEY":
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'max_output_tokens': max_tokens,
                        'temperature': 0.1,  # Lower temperature for stable JSON
                    }
                )
                parsed = self.parse_json_response(response.text)
                
                # Validate we got actual findings, not an error
                if "error" not in parsed:
                    self.logger.info("✅ Real Gemini LLM response received and parsed")
                    return parsed
                else:
                    self.logger.warning(f"⚠️ LLM response parsing failed: {parsed.get('error')} — using fallback analysis")
                    return self._smart_fallback(prompt)
                    
            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'ResourceExhausted' in error_str:
                    self.logger.error(
                        f"🚫 RATE LIMIT EXHAUSTED: Gemini API quota exceeded. "
                        f"The free-tier request limit has been reached. "
                        f"Please check your plan and billing at https://ai.google.dev/gemini-api/docs/rate-limits — "
                        f"using fallback analysis"
                    )
                else:
                    self.logger.warning(f"⚠️ Gemini API call failed: {e} — using fallback analysis")
                return self._smart_fallback(prompt)
        
        self.logger.info("ℹ️ Using fallback snippet analysis (no LLM configured)")
        return self._smart_fallback(prompt)
    
    def _smart_fallback(self, prompt: str) -> Dict[str, Any]:
        """
        Smart fallback that analyzes the actual code snippet in the prompt
        using regex pattern-matching to generate contextually correct findings.
        
        This ensures that even without LLM access, each snippet gets
        unique, relevant findings based on its actual content.
        """
        # Extract the code block from the prompt
        code = self._extract_code_from_prompt(prompt)
        
        # Determine analysis type from prompt
        prompt_upper = prompt.upper()
        # Check LOGIC first because logic prompts contain 'Do NOT check security'
        if "LOGIC" in prompt_upper and "DO NOT CHECK SECURITY" in prompt_upper:
            return self._analyze_logic_patterns(code)
        elif "SECURITY" in prompt_upper:
            return self._analyze_security_patterns(code)
        else:
            return {"findings": [], "confidence": 0.6}
    
    def _extract_code_from_prompt(self, prompt: str) -> str:
        """Extract the code snippet from the agent's prompt."""
        # Look for code between "Code:" and the next section or end
        match = re.search(r'Code:\s*\n(.*?)(?:\n\s*(?:Identify|Check for|Return|Do NOT)|$)', 
                         prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback: look for code between Code: and end
        match = re.search(r'Code:\s*\n(.*)', prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return prompt
    
    # ========== SECURITY PATTERN ANALYSIS ==========
    
    def _analyze_security_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze code for security patterns and return contextualized findings."""
        findings = []
        code_lower = code.lower()
        
        # Pattern 1: SQL Injection (string concatenation with SQL)
        sql_patterns = [
            (r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP).*{', 'f-string SQL query with variable interpolation'),
            (r'(?:SELECT|INSERT|UPDATE|DELETE|DROP).*\+\s*\w+', 'String concatenation in SQL query'),
            (r'(?:SELECT|INSERT|UPDATE|DELETE|DROP).*%s', 'String formatting in SQL query (possible injection)'),
            (r'(?:SELECT|INSERT|UPDATE|DELETE|DROP).*\.format\(', '.format() used in SQL query'),
            (r'execute\s*\(\s*f["\']', 'Direct execution of f-string SQL query'),
        ]
        for pattern, desc in sql_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                findings.append({
                    "type": "sql_injection",
                    "severity": "critical",
                    "description": f"SQL Injection Risk: {desc}",
                    "line": match.group(0).strip()[:100]
                })
                break  # One SQL finding per snippet
        
        # Pattern 2: Code Execution (eval/exec)
        if re.search(r'\beval\s*\(', code):
            match = re.search(r'.*\beval\s*\(.*', code)
            findings.append({
                "type": "code_execution",
                "severity": "critical",
                "description": "Dangerous code execution: eval() can execute arbitrary code from user input",
                "line": match.group(0).strip()[:100] if match else "eval()"
            })
        
        if re.search(r'\bexec\s*\(', code):
            match = re.search(r'.*\bexec\s*\(.*', code)
            findings.append({
                "type": "code_execution",
                "severity": "critical",
                "description": "Dangerous code execution: exec() can execute arbitrary Python statements",
                "line": match.group(0).strip()[:100] if match else "exec()"
            })
        
        # Pattern 3: Insecure Deserialization
        if re.search(r'pickle\.(?:load|loads)\s*\(', code):
            findings.append({
                "type": "insecure_deserialization",
                "severity": "high",
                "description": "Insecure deserialization: pickle.load() can execute arbitrary code from untrusted data",
                "line": re.search(r'.*pickle\.(?:load|loads)\s*\(.*', code).group(0).strip()[:100]
            })
        
        if re.search(r'yaml\.(?:load|unsafe_load)\s*\(', code):
            findings.append({
                "type": "insecure_deserialization",
                "severity": "high",
                "description": "Insecure YAML deserialization: yaml.load() without Loader can execute arbitrary code",
                "line": re.search(r'.*yaml\.(?:load|unsafe_load)\s*\(.*', code).group(0).strip()[:100]
            })
        
        # Pattern 4: Path Traversal
        if re.search(r'open\s*\(.*\+', code) or re.search(r'open\s*\(.*f["\']', code):
            match = re.search(r'.*open\s*\(.*', code)
            findings.append({
                "type": "path_traversal",
                "severity": "high",
                "description": "Path traversal risk: File path constructed from variable input without sanitization",
                "line": match.group(0).strip()[:100] if match else "open(user_input)"
            })
        
        # Pattern 5: Hardcoded Secrets
        secret_patterns = [
            (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', 'Hardcoded password detected'),
            (r'(?:api_key|apikey|secret_key|secret)\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key/secret detected'),
            (r'(?:token|auth_token)\s*=\s*["\'][^"\']+["\']', 'Hardcoded authentication token detected'),
        ]
        for pattern, desc in secret_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                findings.append({
                    "type": "hardcoded_secret",
                    "severity": "high",
                    "description": f"Security risk: {desc}",
                    "line": match.group(0).strip()[:100]
                })
                break
        
        # Pattern 6: Missing Input Validation
        if re.search(r'request\.(args|form|json|data|files)', code):
            if not re.search(r'(?:validate|sanitize|check|verify|isinstance|int\(|float\()', code_lower):
                match = re.search(r'.*request\.(?:args|form|json|data|files).*', code)
                findings.append({
                    "type": "input_validation",
                    "severity": "medium",
                    "description": "Missing input validation: User input from request is used without sanitization",
                    "line": match.group(0).strip()[:100] if match else "request.args/form/json"
                })
        
        # Pattern 7: Command execution via subprocess/os.system
        if re.search(r'(?:os\.system|subprocess\.call|subprocess\.run|subprocess\.Popen)\s*\(', code):
            match = re.search(r'.*(?:os\.system|subprocess\.\w+)\s*\(.*', code)
            findings.append({
                "type": "command_injection",
                "severity": "critical",
                "description": "Command injection risk: System command execution with potential user input",
                "line": match.group(0).strip()[:100] if match else "os.system()"
            })
        
        # If no patterns found, report clean
        if not findings:
            findings.append({
                "type": "no_issues",
                "severity": "info",
                "description": "No obvious security vulnerabilities detected in this code snippet",
                "line": ""
            })
        
        confidence = min(0.9, 0.6 + (len(findings) * 0.1))
        return {"findings": findings, "confidence": confidence}
    
    # ========== LOGIC PATTERN ANALYSIS ==========
    
    def _analyze_logic_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze code for logic issues and return contextualized findings."""
        findings = []
        
        # Pattern 1: Infinite Loop Risk
        if re.search(r'while\s+True\s*:', code):
            # Check if there's a break statement in the loop
            has_break = bool(re.search(r'\bbreak\b', code))
            if has_break:
                findings.append({
                    "issue": "conditional_infinite_loop",
                    "severity": "medium",
                    "description": "while True loop with conditional break — may loop infinitely if break condition is never met"
                })
            else:
                findings.append({
                    "issue": "infinite_loop",
                    "severity": "high",
                    "description": "Unconditional while True loop without any break statement — will cause infinite execution"
                })
        
        # Check for while loops with mutable conditions
        while_loops = re.findall(r'while\s+(\w+)\s*:', code)
        for var in while_loops:
            if var != 'True' and var != 'False':
                # Check if the variable is ever modified in the loop
                if not re.search(rf'{var}\s*=', code):
                    findings.append({
                        "issue": "potential_infinite_loop",
                        "severity": "medium",
                        "description": f"Loop variable '{var}' may not be modified inside the loop body, risking infinite iteration"
                    })
        
        # Pattern 2: Unreachable Code
        lines = code.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped in ('break', 'return', 'continue', 'raise', 'sys.exit()'):
                # Check if there's non-comment code after this in the same block
                indentation = len(line) - len(line.lstrip())
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    if not next_stripped or next_stripped.startswith('#'):
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent >= indentation and next_stripped:
                        findings.append({
                            "issue": "unreachable_code",
                            "severity": "medium",
                            "description": f"Code after '{stripped}' statement at this indentation level may be unreachable"
                        })
                        break
                break  # Only report once
        
        # Pattern 3: Off-by-one errors
        if re.search(r'range\(\s*len\(.*?\)\s*\+\s*1\s*\)', code):
            findings.append({
                "issue": "off_by_one",
                "severity": "medium",
                "description": "Potential off-by-one error: range(len(x) + 1) iterates one past the last valid index"
            })
        
        if re.search(r'\[\s*len\(.*?\)\s*\]', code):
            findings.append({
                "issue": "off_by_one",
                "severity": "high",
                "description": "Index out of bounds: accessing index len(x) exceeds the last valid index (len(x) - 1)"
            })
        
        # Pattern 4: Missing edge case handling
        if re.search(r'def\s+\w+\s*\([^)]*\)\s*:', code):
            # Check for missing None/empty checks
            params = re.findall(r'def\s+\w+\s*\(([^)]*)\)', code)
            if params and '=' not in params[0]:  # Required params without defaults
                if not re.search(r'if\s+(?:not\s+)?\w+\s+is\s+(?:not\s+)?None', code) and \
                   not re.search(r'if\s+\w+\s*:', code):
                    findings.append({
                        "issue": "missing_null_check",
                        "severity": "low",
                        "description": "Function parameters are not checked for None/empty values — may cause unexpected errors"
                    })
        
        # Pattern 5: Division by zero risk
        if re.search(r'/\s*\w+', code) and not re.search(r'if\s+.*!=\s*0|if\s+.*>\s*0', code):
            div_match = re.search(r'.*[/](?!/)\s*\w+.*', code)  # Avoid matching //
            if div_match and 'import' not in div_match.group(0):
                findings.append({
                    "issue": "division_by_zero",
                    "severity": "medium",
                    "description": "Potential division by zero: divisor variable is not checked before division"
                })
        
        # Pattern 6: Incorrect comparison
        if re.search(r'==\s*True|==\s*False|==\s*None', code):
            findings.append({
                "issue": "incorrect_comparison",
                "severity": "low",
                "description": "Consider using 'is' instead of '==' for comparing with True/False/None"
            })
        
        # Pattern 7: Deeply nested code
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent)
        
        nesting_level = max_indent // 4
        if nesting_level >= 4:
            findings.append({
                "issue": "deep_nesting",
                "severity": "medium",
                "description": f"Deeply nested code ({nesting_level} levels) — consider refactoring to reduce complexity"
            })
        
        # Pattern 8: Recursion without base case
        func_names = re.findall(r'def\s+(\w+)\s*\(', code)
        for func_name in func_names:
            if re.search(rf'\b{func_name}\s*\(', code.split(f'def {func_name}', 1)[-1] if f'def {func_name}' in code else ''):
                if not re.search(r'if\s+.*:\s*\n\s*return', code):
                    findings.append({
                        "issue": "recursion_risk",
                        "severity": "high",
                        "description": f"Recursive function '{func_name}' may lack a proper base case, risking stack overflow"
                    })
        
        # If no patterns found, report clean
        if not findings:
            findings.append({
                "issue": "no_issues",
                "severity": "info",
                "description": "No obvious logic issues detected in this code snippet"
            })
        
        confidence = min(0.85, 0.6 + (len(findings) * 0.08))
        return {"findings": findings, "confidence": confidence}
    
    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        Handles responses wrapped in markdown code blocks (```json ... ```).
        """
        try:
            # Step 1: Strip markdown code block wrappers if present
            cleaned = response_text.strip()
            
            # Remove ```json ... ``` wrapping
            if cleaned.startswith('```'):
                # Remove opening ``` line (with optional language tag)
                cleaned = re.sub(r'^```\w*\s*\n?', '', cleaned)
                # Remove closing ```
                cleaned = re.sub(r'\n?```\s*$', '', cleaned)
                cleaned = cleaned.strip()
            
            # Step 2: Try direct parse first
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Step 3: Find the outermost JSON object
            # Use a bracket-counting approach instead of simple find
            brace_depth = 0
            json_start = -1
            json_end = -1
            
            for i, char in enumerate(cleaned):
                if char == '{':
                    if brace_depth == 0:
                        json_start = i
                    brace_depth += 1
                elif char == '}':
                    brace_depth -= 1
                    if brace_depth == 0 and json_start != -1:
                        json_end = i + 1
                        break
            
            if json_start != -1 and json_end > json_start:
                json_text = cleaned[json_start:json_end]
                return json.loads(json_text)
            
            return {"error": "No JSON found in response", "raw": response_text[:200]}
        
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in response: {e}", "raw": response_text[:200]}
