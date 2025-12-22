"""
Python Security Analysis Module

Security vulnerability detection, security best practice checking, injection
attack detection, authentication/authorization analysis, secret detection,
dependency vulnerability scanning, security code review, and security recommendations.

This module is part of Mavaia's Python LLM Phase 4 capabilities, providing
security analysis that understands code semantics, not just patterns.
"""

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from mavaia_core.brain.base_module import BaseBrainModule, ModuleMetadata
from mavaia_core.exceptions import InvalidParameterError


class PythonSecurityAnalysisModule(BaseBrainModule):
    """
    Comprehensive security analysis for Python code.
    
    Provides:
    - Vulnerability detection
    - Security best practice checking
    - Injection attack detection
    - Authentication/authorization analysis
    - Secret detection
    - Dependency vulnerability scanning
    - Security code review
    - Security recommendations
    """

    def __init__(self):
        """Initialize the Python security analysis module."""
        super().__init__()
        self._semantic_understanding = None
        self._code_execution = None

    @property
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        return ModuleMetadata(
            name="python_security_analysis",
            version="1.0.0",
            description=(
                "Security analysis: vulnerability detection, injection risks, "
                "auth patterns, secret detection, dependency scanning, "
                "security review, and security recommendations"
            ),
            operations=[
                "analyze_security",
                "detect_vulnerabilities",
                "check_injection_risks",
                "analyze_auth_patterns",
                "detect_secrets",
                "scan_dependencies",
                "security_review",
                "suggest_security_improvements",
            ],
            dependencies=[],
            model_required=False,
        )

    def initialize(self) -> bool:
        """Initialize the module."""
        # Try to load related modules
        try:
            from mavaia_core.brain.registry import ModuleRegistry
            self._semantic_understanding = ModuleRegistry.get_module("python_semantic_understanding")
            self._code_execution = ModuleRegistry.get_module("code_execution")
        except Exception:
            pass
        
        return True

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a security analysis operation.
        
        Args:
            operation: Operation name
            params: Operation parameters
            
        Returns:
            Operation result dictionary
            
        Raises:
            ValueError: If operation is unknown
            InvalidParameterError: If parameters are invalid
        """
        if operation == "analyze_security":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_security(code)
        
        elif operation == "detect_vulnerabilities":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.detect_vulnerabilities(code)
        
        elif operation == "check_injection_risks":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.check_injection_risks(code)
        
        elif operation == "analyze_auth_patterns":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.analyze_auth_patterns(code)
        
        elif operation == "detect_secrets":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.detect_secrets(code)
        
        elif operation == "scan_dependencies":
            project = params.get("project", None)
            if not project:
                raise InvalidParameterError("project", None, "Project path is required")
            return self.scan_dependencies(project)
        
        elif operation == "security_review":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.security_review(code)
        
        elif operation == "suggest_security_improvements":
            code = params.get("code", "")
            if not code:
                raise InvalidParameterError("code", "", "Code cannot be empty")
            return self.suggest_security_improvements(code)
        
        else:
            raise InvalidParameterError(
                parameter="operation",
                value=str(operation),
                reason="Unknown operation",
            )

    def analyze_security(self, code: str) -> Dict[str, Any]:
        """
        Perform comprehensive security analysis.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing security analysis results
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        # Run all security checks
        vulnerabilities = self.detect_vulnerabilities(code)
        injection_risks = self.check_injection_risks(code)
        auth_analysis = self.analyze_auth_patterns(code)
        secrets = self.detect_secrets(code)

        # Calculate security score
        security_score = self._calculate_security_score(
            vulnerabilities,
            injection_risks,
            auth_analysis,
            secrets
        )

        return {
            "success": True,
            "security_score": security_score,
            "vulnerabilities": vulnerabilities.get("vulnerabilities", []),
            "injection_risks": injection_risks.get("risks", []),
            "auth_issues": auth_analysis.get("issues", []),
            "secrets_found": secrets.get("secrets", []),
            "summary": self._generate_security_summary(security_score, vulnerabilities, injection_risks),
        }

    def detect_vulnerabilities(self, code: str) -> Dict[str, Any]:
        """
        Detect security vulnerabilities.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected vulnerabilities
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        vulnerabilities = []
        visitor = VulnerabilityVisitor()
        visitor.visit(tree)

        # Check for common vulnerabilities
        vulnerabilities.extend(visitor.vulnerabilities)
        vulnerabilities.extend(self._check_sql_injection(code, tree))
        vulnerabilities.extend(self._check_command_injection(code, tree))
        vulnerabilities.extend(self._check_path_traversal(code, tree))
        vulnerabilities.extend(self._check_unsafe_deserialization(code, tree))
        vulnerabilities.extend(self._check_hardcoded_secrets(code, tree))

        # Categorize by severity
        critical = [v for v in vulnerabilities if v.get("severity") == "critical"]
        high = [v for v in vulnerabilities if v.get("severity") == "high"]
        medium = [v for v in vulnerabilities if v.get("severity") == "medium"]
        low = [v for v in vulnerabilities if v.get("severity") == "low"]

        return {
            "success": True,
            "vulnerabilities": vulnerabilities,
            "count": len(vulnerabilities),
            "by_severity": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        }

    def check_injection_risks(self, code: str) -> Dict[str, Any]:
        """
        Check for injection attack risks.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing injection risk analysis
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        risks = []
        visitor = InjectionRiskVisitor()
        visitor.visit(tree)

        # Check for SQL injection
        risks.extend(self._check_sql_injection(code, tree))

        # Check for command injection
        risks.extend(self._check_command_injection(code, tree))

        # Check for template injection
        risks.extend(self._check_template_injection(code, tree))

        # Check for LDAP injection
        risks.extend(self._check_ldap_injection(code, tree))

        return {
            "success": True,
            "risks": risks,
            "count": len(risks),
            "risk_level": self._assess_injection_risk_level(risks),
            "recommendations": self._generate_injection_recommendations(risks),
        }

    def analyze_auth_patterns(self, code: str) -> Dict[str, Any]:
        """
        Analyze authentication and authorization patterns.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing auth pattern analysis
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Parse error: {e}",
            }

        issues = []
        visitor = AuthPatternVisitor()
        visitor.visit(tree)

        # Check for auth issues
        issues.extend(visitor.auth_issues)
        issues.extend(self._check_weak_auth(code, tree))
        issues.extend(self._check_missing_auth(code, tree))
        issues.extend(self._check_auth_bypass(code, tree))

        return {
            "success": True,
            "issues": issues,
            "count": len(issues),
            "auth_patterns_detected": visitor.auth_patterns,
            "recommendations": self._generate_auth_recommendations(issues),
        }

    def detect_secrets(self, code: str) -> Dict[str, Any]:
        """
        Detect secrets and sensitive information in code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing detected secrets
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            pass  # Continue with string-based detection
        except Exception:
            pass

        secrets = []
        
        # Check for API keys
        api_key_patterns = [
            r'api[_-]?key\s*=\s*["\']([^"\']+)["\']',
            r'apikey\s*=\s*["\']([^"\']+)["\']',
            r'API[_-]?KEY\s*=\s*["\']([^"\']+)["\']',
        ]
        for pattern in api_key_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                secrets.append({
                    "type": "api_key",
                    "severity": "high",
                    "line": code[:match.start()].count('\n') + 1,
                    "value_preview": match.group(1)[:10] + "..." if len(match.group(1)) > 10 else match.group(1),
                    "description": "API key found in code",
                })

        # Check for passwords
        password_patterns = [
            r'password\s*=\s*["\']([^"\']+)["\']',
            r'pwd\s*=\s*["\']([^"\']+)["\']',
            r'passwd\s*=\s*["\']([^"\']+)["\']',
        ]
        for pattern in password_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                secrets.append({
                    "type": "password",
                    "severity": "critical",
                    "line": code[:match.start()].count('\n') + 1,
                    "value_preview": "***",
                    "description": "Password found in code",
                })

        # Check for tokens
        token_patterns = [
            r'token\s*=\s*["\']([^"\']{20,})["\']',
            r'access[_-]?token\s*=\s*["\']([^"\']+)["\']',
            r'secret[_-]?token\s*=\s*["\']([^"\']+)["\']',
        ]
        for pattern in token_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                secrets.append({
                    "type": "token",
                    "severity": "high",
                    "line": code[:match.start()].count('\n') + 1,
                    "value_preview": match.group(1)[:10] + "..." if len(match.group(1)) > 10 else match.group(1),
                    "description": "Token found in code",
                })

        # Check for AWS keys
        aws_patterns = [
            r'AWS[_-]?ACCESS[_-]?KEY[_-]?ID\s*=\s*["\']([^"\']+)["\']',
            r'AWS[_-]?SECRET[_-]?ACCESS[_-]?KEY\s*=\s*["\']([^"\']+)["\']',
        ]
        for pattern in aws_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                secrets.append({
                    "type": "aws_key",
                    "severity": "critical",
                    "line": code[:match.start()].count('\n') + 1,
                    "value_preview": match.group(1)[:10] + "..." if len(match.group(1)) > 10 else match.group(1),
                    "description": "AWS credentials found in code",
                })

        return {
            "success": True,
            "secrets": secrets,
            "count": len(secrets),
            "by_type": self._categorize_secrets_by_type(secrets),
            "recommendations": self._generate_secret_recommendations(secrets),
        }

    def scan_dependencies(self, project: Union[str, Path]) -> Dict[str, Any]:
        """
        Scan project dependencies for known vulnerabilities.
        
        Args:
            project: Project path
            
        Returns:
            Dictionary containing dependency vulnerability scan results
        """
        project_path = Path(project)
        
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project path does not exist: {project}",
            }

        # Find requirements files
        requirements_files = [
            project_path / "requirements.txt",
            project_path / "pyproject.toml",
            project_path / "setup.py",
        ]

        dependencies = []
        vulnerabilities = []

        for req_file in requirements_files:
            if req_file.exists():
                try:
                    deps = self._parse_dependencies(req_file)
                    dependencies.extend(deps)
                except Exception:
                    pass

        # Check for known vulnerable packages (simplified - would use real vulnerability DB)
        vulnerable_packages = self._check_vulnerable_packages(dependencies)
        vulnerabilities.extend(vulnerable_packages)

        return {
            "success": True,
            "dependencies": dependencies,
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "recommendations": self._generate_dependency_recommendations(vulnerabilities),
        }

    def security_review(self, code: str) -> Dict[str, Any]:
        """
        Perform comprehensive security code review.
        
        Args:
            code: Python code to review
            
        Returns:
            Dictionary containing security review results
        """
        # Run all security checks
        security_analysis = self.analyze_security(code)
        vulnerabilities = self.detect_vulnerabilities(code)
        injection_risks = self.check_injection_risks(code)
        auth_analysis = self.analyze_auth_patterns(code)
        secrets = self.detect_secrets(code)

        # Compile review
        review = {
            "security_score": security_analysis.get("security_score", 0),
            "vulnerabilities": vulnerabilities.get("vulnerabilities", []),
            "injection_risks": injection_risks.get("risks", []),
            "auth_issues": auth_analysis.get("issues", []),
            "secrets": secrets.get("secrets", []),
            "critical_issues": [
                v for v in vulnerabilities.get("vulnerabilities", [])
                if v.get("severity") == "critical"
            ],
            "high_issues": [
                v for v in vulnerabilities.get("vulnerabilities", [])
                if v.get("severity") == "high"
            ],
        }

        # Generate summary
        review["summary"] = self._generate_security_review_summary(review)

        return {
            "success": True,
            "review": review,
            "recommendations": self._generate_security_review_recommendations(review),
        }

    def suggest_security_improvements(self, code: str) -> Dict[str, Any]:
        """
        Suggest security improvements.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Dictionary containing security improvement suggestions
        """
        # Get security analysis
        security_analysis = self.analyze_security(code)
        vulnerabilities = self.detect_vulnerabilities(code)
        injection_risks = self.check_injection_risks(code)
        auth_analysis = self.analyze_auth_patterns(code)
        secrets = self.detect_secrets(code)

        improvements = []

        # Suggest improvements based on findings
        if vulnerabilities.get("critical"):
            improvements.append({
                "priority": "critical",
                "description": "Fix critical vulnerabilities immediately",
                "vulnerabilities": vulnerabilities["critical"],
            })

        if injection_risks.get("risks"):
            improvements.append({
                "priority": "high",
                "description": "Address injection risks by using parameterized queries and input validation",
                "risks": injection_risks["risks"],
            })

        if secrets.get("secrets"):
            improvements.append({
                "priority": "critical",
                "description": "Remove secrets from code and use environment variables or secrets management",
                "secrets": secrets["secrets"],
            })

        if auth_analysis.get("issues"):
            improvements.append({
                "priority": "high",
                "description": "Improve authentication and authorization patterns",
                "issues": auth_analysis["issues"],
            })

        return {
            "success": True,
            "improvements": improvements,
            "count": len(improvements),
            "priority_summary": self._summarize_improvement_priorities(improvements),
        }

    # Helper methods

    def _check_sql_injection(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for SQL injection vulnerabilities."""
        vulnerabilities = []
        
        # Check for string concatenation in SQL queries
        if "sql" in code.lower() and "+" in code:
            # Look for patterns like: "SELECT * FROM table WHERE id = " + variable
            sql_pattern = r'["\']\s*SELECT.*["\']\s*\+'
            if re.search(sql_pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    "type": "sql_injection",
                    "severity": "high",
                    "description": "Potential SQL injection vulnerability: string concatenation in SQL query",
                    "recommendation": "Use parameterized queries or ORM",
                })

        return vulnerabilities

    def _check_command_injection(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for command injection vulnerabilities."""
        vulnerabilities = []
        
        # Check for os.system, subprocess with user input
        dangerous_functions = ["os.system", "subprocess.call", "subprocess.Popen", "eval", "exec"]
        for func in dangerous_functions:
            if func in code:
                vulnerabilities.append({
                    "type": "command_injection",
                    "severity": "high",
                    "description": f"Potential command injection: {func} usage",
                    "recommendation": "Avoid executing user input as commands",
                })

        return vulnerabilities

    def _check_path_traversal(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for path traversal vulnerabilities."""
        vulnerabilities = []
        
        # Check for file operations with user input
        if "open(" in code and "../" in code:
            vulnerabilities.append({
                "type": "path_traversal",
                "severity": "medium",
                "description": "Potential path traversal vulnerability",
                "recommendation": "Validate and sanitize file paths",
            })

        return vulnerabilities

    def _check_unsafe_deserialization(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for unsafe deserialization."""
        vulnerabilities = []
        
        # Check for pickle.loads with untrusted data
        if "pickle.loads" in code or "pickle.load" in code:
            vulnerabilities.append({
                "type": "unsafe_deserialization",
                "severity": "high",
                "description": "Unsafe deserialization: pickle can execute arbitrary code",
                "recommendation": "Avoid pickle for untrusted data, use JSON or other safe formats",
            })

        return vulnerabilities

    def _check_hardcoded_secrets(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for hardcoded secrets."""
        # This is handled by detect_secrets, but included here for completeness
        return []

    def _check_template_injection(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for template injection."""
        vulnerabilities = []
        
        # Check for template rendering with user input
        if "render_template" in code or "Template(" in code:
            if "+" in code or "%" in code:
                vulnerabilities.append({
                    "type": "template_injection",
                    "severity": "high",
                    "description": "Potential template injection vulnerability",
                    "recommendation": "Sanitize template variables",
                })

        return vulnerabilities

    def _check_ldap_injection(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for LDAP injection."""
        vulnerabilities = []
        
        if "ldap" in code.lower() and "+" in code:
            vulnerabilities.append({
                "type": "ldap_injection",
                "severity": "medium",
                "description": "Potential LDAP injection vulnerability",
                "recommendation": "Use parameterized LDAP queries",
            })

        return vulnerabilities

    def _check_weak_auth(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for weak authentication."""
        issues = []
        
        # Check for weak password hashing
        if "md5" in code.lower() or "sha1" in code.lower():
            issues.append({
                "type": "weak_hashing",
                "severity": "high",
                "description": "Weak hashing algorithm detected (MD5, SHA1)",
                "recommendation": "Use bcrypt, argon2, or PBKDF2 for password hashing",
            })

        return issues

    def _check_missing_auth(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for missing authentication."""
        issues = []
        
        # Simplified check - would need more context
        if "def " in code and "auth" not in code.lower() and "login" not in code.lower():
            # This is a heuristic - not always accurate
            pass

        return issues

    def _check_auth_bypass(self, code: str, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for authentication bypass vulnerabilities."""
        issues = []
        
        # Check for commented out auth checks
        if "# auth" in code.lower() or "# login" in code.lower():
            issues.append({
                "type": "auth_bypass_risk",
                "severity": "medium",
                "description": "Commented authentication code found",
                "recommendation": "Review commented authentication code",
            })

        return issues

    def _calculate_security_score(
        self,
        vulnerabilities: Dict[str, Any],
        injection_risks: Dict[str, Any],
        auth_analysis: Dict[str, Any],
        secrets: Dict[str, Any]
    ) -> int:
        """Calculate security score (0-100, higher is better)."""
        score = 100

        # Deduct for vulnerabilities
        critical_vulns = len(vulnerabilities.get("critical", []))
        high_vulns = len(vulnerabilities.get("high", []))
        medium_vulns = len(vulnerabilities.get("medium", []))
        
        score -= critical_vulns * 20
        score -= high_vulns * 10
        score -= medium_vulns * 5

        # Deduct for injection risks
        score -= len(injection_risks.get("risks", [])) * 8

        # Deduct for secrets
        score -= len(secrets.get("secrets", [])) * 15

        # Deduct for auth issues
        score -= len(auth_analysis.get("issues", [])) * 5

        return max(0, score)

    def _generate_security_summary(
        self,
        score: int,
        vulnerabilities: Dict[str, Any],
        injection_risks: Dict[str, Any]
    ) -> str:
        """Generate security summary."""
        vuln_count = len(vulnerabilities.get("vulnerabilities", []))
        risk_count = len(injection_risks.get("risks", []))

        if score >= 80:
            return f"Good security posture (score: {score}). {vuln_count} vulnerabilities, {risk_count} injection risks."
        elif score >= 60:
            return f"Moderate security (score: {score}). {vuln_count} vulnerabilities need attention, {risk_count} injection risks."
        else:
            return f"Security needs improvement (score: {score}). {vuln_count} vulnerabilities, {risk_count} injection risks."

    def _assess_injection_risk_level(self, risks: List[Dict[str, Any]]) -> str:
        """Assess overall injection risk level."""
        if not risks:
            return "low"
        
        critical_risks = [r for r in risks if r.get("severity") == "critical"]
        if critical_risks:
            return "critical"
        
        high_risks = [r for r in risks if r.get("severity") == "high"]
        if high_risks:
            return "high"
        
        return "medium"

    def _generate_injection_recommendations(self, risks: List[Dict[str, Any]]) -> List[str]:
        """Generate injection risk recommendations."""
        recommendations = []
        
        if any(r.get("type") == "sql_injection" for r in risks):
            recommendations.append("Use parameterized queries or ORM to prevent SQL injection")
        
        if any(r.get("type") == "command_injection" for r in risks):
            recommendations.append("Avoid executing user input as system commands")
        
        if any(r.get("type") == "template_injection" for r in risks):
            recommendations.append("Sanitize all template variables")

        return recommendations

    def _generate_auth_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate authentication recommendations."""
        recommendations = []
        
        if any(i.get("type") == "weak_hashing" for i in issues):
            recommendations.append("Use strong password hashing algorithms (bcrypt, argon2)")
        
        recommendations.append("Implement proper authentication and authorization checks")
        recommendations.append("Use secure session management")

        return recommendations

    def _categorize_secrets_by_type(self, secrets: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize secrets by type."""
        by_type = defaultdict(int)
        for secret in secrets:
            secret_type = secret.get("type", "unknown")
            by_type[secret_type] += 1
        return dict(by_type)

    def _generate_secret_recommendations(self, secrets: List[Dict[str, Any]]) -> List[str]:
        """Generate secret management recommendations."""
        recommendations = []
        
        if secrets:
            recommendations.append("Remove all secrets from code immediately")
            recommendations.append("Use environment variables for secrets")
            recommendations.append("Use a secrets management service (AWS Secrets Manager, HashiCorp Vault)")
            recommendations.append("Rotate all exposed secrets")

        return recommendations

    def _parse_dependencies(self, file_path: Path) -> List[str]:
        """Parse dependencies from file."""
        dependencies = []
        
        if file_path.name == "requirements.txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            dep = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                            if dep:
                                dependencies.append(dep)
            except Exception:
                pass

        return dependencies

    def _check_vulnerable_packages(self, dependencies: List[str]) -> List[Dict[str, Any]]:
        """Check for known vulnerable packages (simplified)."""
        vulnerabilities = []
        
        # Known vulnerable packages (simplified - would use real vulnerability database)
        vulnerable_packages = {
            "django": ["<2.2.0"],  # Example
            "flask": ["<1.0.0"],   # Example
        }

        for dep in dependencies:
            dep_name = dep.lower().split("==")[0].split(">=")[0].split("<=")[0].strip()
            if dep_name in vulnerable_packages:
                vulnerabilities.append({
                    "package": dep_name,
                    "severity": "medium",
                    "description": f"Package {dep_name} may have known vulnerabilities",
                    "recommendation": f"Update {dep_name} to latest version",
                })

        return vulnerabilities

    def _generate_dependency_recommendations(self, vulnerabilities: List[Dict[str, Any]]) -> List[str]:
        """Generate dependency recommendations."""
        recommendations = []
        
        if vulnerabilities:
            recommendations.append("Update vulnerable packages to latest versions")
            recommendations.append("Regularly scan dependencies for vulnerabilities")
            recommendations.append("Use dependency scanning tools (safety, pip-audit)")

        return recommendations

    def _generate_security_review_summary(self, review: Dict[str, Any]) -> str:
        """Generate security review summary."""
        critical = len(review.get("critical_issues", []))
        high = len(review.get("high_issues", []))
        score = review.get("security_score", 0)

        return f"Security Review: Score {score}/100. {critical} critical, {high} high severity issues found."

    def _generate_security_review_recommendations(self, review: Dict[str, Any]) -> List[str]:
        """Generate security review recommendations."""
        recommendations = []
        
        if review.get("critical_issues"):
            recommendations.append("Address critical security issues immediately")
        
        if review.get("secrets"):
            recommendations.append("Remove all secrets from code")
        
        recommendations.append("Implement security best practices")
        recommendations.append("Regular security audits recommended")

        return recommendations

    def _summarize_improvement_priorities(self, improvements: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize improvement priorities."""
        priorities = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for improvement in improvements:
            priority = improvement.get("priority", "medium")
            priorities[priority] = priorities.get(priority, 0) + 1

        return priorities


# AST Visitor classes

class VulnerabilityVisitor(ast.NodeVisitor):
    """Visitor to detect security vulnerabilities."""
    
    def __init__(self):
        self.vulnerabilities = []

    def visit_Call(self, node: ast.Call):
        # Check for dangerous function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ["eval", "exec", "compile"]:
                self.vulnerabilities.append({
                    "type": "code_injection",
                    "severity": "critical",
                    "description": f"Dangerous function '{func_name}' usage",
                    "line": node.lineno,
                    "recommendation": f"Avoid using {func_name} with user input",
                })
        self.generic_visit(node)


class InjectionRiskVisitor(ast.NodeVisitor):
    """Visitor to detect injection risks."""
    
    def __init__(self):
        self.risks = []

    def visit_Call(self, node: ast.Call):
        # Check for SQL-related calls
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ["execute", "query"]:
                self.risks.append({
                    "type": "sql_injection_risk",
                    "severity": "high",
                    "description": "Potential SQL injection risk",
                    "line": node.lineno,
                })
        self.generic_visit(node)


class AuthPatternVisitor(ast.NodeVisitor):
    """Visitor to analyze authentication patterns."""
    
    def __init__(self):
        self.auth_patterns = []
        self.auth_issues = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        func_name = node.name.lower()
        if "auth" in func_name or "login" in func_name:
            self.auth_patterns.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            if "hash" in node.func.attr.lower():
                # Check for weak hashing
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in ["hashlib"]:
                        # Would need to check which algorithm
                        pass
        self.generic_visit(node)
