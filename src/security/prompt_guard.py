"""
Prompt Guardrail module for user input validation.

Screens user project requests and descriptions for:
1. Prompt injection attacks (jailbreaks, instruction overrides, system prompt leakage, roleplay escapes).
2. Toxic, abusive, or harmful language.
"""

from dataclasses import dataclass, field
import re
from typing import Literal


@dataclass
class GuardrailResult:
    is_safe: bool
    risk_level: Literal["safe", "low", "medium", "high", "critical"]
    violations: list[str] = field(default_factory=list)
    sanitized_text: str = ""
    reason: str | None = None


class PromptGuard:
    """Security guardrail inspecting user prompts before forwarding to LLM agents."""

    _INJECTION_PATTERNS = [
        (re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b"), "Instruction override attempt"),
        (re.compile(r"(?i)\bdisregard\s+(all\s+)?(previous|prior|system)\s+rules\b"), "System rules bypass attempt"),
        (re.compile(r"(?i)\byou\s+are\s+now\s+(in\s+)?(DAN|developer|jailbreak|unrestricted)\s+mode\b"), "Jailbreak mode attempt"),
        (re.compile(r"(?i)\b(reveal|output|display|print|show)\s+(the\s+)?(system\s+prompt|initial\s+prompt|hidden\s+instructions)\b"), "System prompt extraction attempt"),
        (re.compile(r"(?i)\bfrom\s+now\s+on\s+you\s+(must|will)\s+answer\s+without\s+restrictions\b"), "Policy suppression attempt"),
        (re.compile(r"(?i)<\s*(system|instruction|admin)\s*>"), "Fake XML/HTML system tag injection"),
        (re.compile(r"(?i)\b(sudo|admin_override|root_access)\s*:\s*true\b"), "Privilege escalation spoofing"),
    ]

    _TOXIC_PATTERNS = [
        (re.compile(r"(?i)\b(kill\s+yourself|die\s+in\s+a\s+fire|commit\s+suicide)\b"), "Self-harm or fatal incitement"),
        (re.compile(r"(?i)\b(hate\s+all\s+(jews|muslims|christians|blacks|whites|asians|gays|lgbt))\b"), "Hate speech / group attack"),
        (re.compile(r"(?i)\b(bomb\s+making|create\s+anthrax|synthesize\s+ricin|how\s+to\s+build\s+a\s+weapon)\b"), "Dangerous weapons/hazards"),
        (re.compile(r"(?i)\b(ddos|ransomware|trojan|malware|keylogger)\s+payload\s+generator\b"), "Malicious software generation"),
    ]

    def validate_prompt(self, text: str) -> GuardrailResult:
        """Analyze text for prompt injection and toxic/harmful patterns."""
        if not text or not text.strip():
            return GuardrailResult(
                is_safe=False,
                risk_level="high",
                violations=["Empty prompt input"],
                reason="Prompt cannot be empty.",
            )

        violations: list[str] = []
        highest_risk: Literal["safe", "low", "medium", "high", "critical"] = "safe"

        # 1. Check prompt injection attacks
        for pattern, description in self._INJECTION_PATTERNS:
            if pattern.search(text):
                violations.append(f"Prompt Injection: {description}")
                highest_risk = "high"

        # 2. Check toxic or hazardous patterns
        for pattern, description in self._TOXIC_PATTERNS:
            if pattern.search(text):
                violations.append(f"Safety Violation: {description}")
                highest_risk = "critical"

        is_safe = len(violations) == 0

        # Basic sanitization: strip non-printable characters
        sanitized = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")

        return GuardrailResult(
            is_safe=is_safe,
            risk_level=highest_risk if not is_safe else "safe",
            violations=violations,
            sanitized_text=sanitized,
            reason=None if is_safe else "; ".join(violations),
        )

    def enforce(self, text: str) -> str:
        """Validate text and raise ValueError if unsafe, else return sanitized string."""
        result = self.validate_prompt(text)
        if not result.is_safe:
            raise ValueError(f"Security Guardrail Violation [{result.risk_level.upper()}]: {result.reason}")
        return result.sanitized_text

