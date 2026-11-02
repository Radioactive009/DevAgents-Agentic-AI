"""
Prompt Variance Engine.

Allows injecting variances across:
1. Architectural style: REACT (Thought/Action/Observation) vs FEW-SHOT vs DIRECT SCHEMA.
2. Persona: DEFENSIVE_SECURITY vs PRAGMATIC_FAST.
3. Content level: MINIMAL vs ENTERPRISE_DETAILED.
"""

from enum import Enum
from pydantic import BaseModel, Field


class PromptArchitecture(str, Enum):
    DIRECT_SCHEMA = "direct_schema"
    REACT = "react"
    FEW_SHOT = "few_shot"


class PromptPersona(str, Enum):
    PRAGMATIC_ARCHITECT = "pragmatic_architect"
    DEFENSIVE_SECURITY_ARCHITECT = "defensive_security_architect"


class PromptVarianceConfig(BaseModel):
    architecture: PromptArchitecture = PromptArchitecture.DIRECT_SCHEMA
    persona: PromptPersona = PromptPersona.PRAGMATIC_ARCHITECT
    include_threat_modeling: bool = False
    max_components: int = Field(default=5, ge=2, le=10)


class PromptVarianceManager:
    """Formats prompts according to the selected architecture and persona variances."""

    _PERSONA_BACKSTORIES = {
        PromptPersona.PRAGMATIC_ARCHITECT: (
            "You are a pragmatic, delivery-focused software architect. "
            "You design small, clean, testable applications without overengineering. "
            "Keep component count minimal and prioritize maintainability."
        ),
        PromptPersona.DEFENSIVE_SECURITY_ARCHITECT: (
            "You are a security-first defensive software architect. "
            "You design hardened applications with strict input validation, principle of least "
            "privilege, defensive boundaries, and proactive risk mitigation."
        ),
    }

    _FEW_SHOT_EXEMPLAR = (
        "--- FEW-SHOT DEMONSTRATION EXAMPLE ---\n"
        "Input Project: Note Service (Python, Features: Create note, Get note)\n"
        "Exemplar Architecture Plan:\n"
        "  Summary: Minimal FastAPI service storing notes in an in-memory dictionary.\n"
        "  Components: ['FastAPI Routes', 'Note Pydantic Model', 'InMemoryRepository', 'Pytest Suite']\n"
        "  Proposed Files: ['app.py', 'models.py', 'store.py', 'tests/test_api.py']\n"
        "  Implementation Steps: ['1. Define schema', '2. Store methods', '3. Endpoints', '4. Tests']\n"
        "  Acceptance Criteria: ['Valid notes stored with UUID', 'Notes retrievable by ID', 'Tests pass']\n"
        "  Risks: ['In-memory store resets on restart']\n"
        "--- END FEW-SHOT EXAMPLE ---\n"
    )

    _REACT_INSTRUCTIONS = (
        "--- REACT ARCHITECTURE PATTERN ---\n"
        "Reason through this task step-by-step using the ReAct loop:\n"
        "Thought: Analyze the user requirements and identify essential architectural boundaries.\n"
        "Action: Deconstruct the system into distinct components and files.\n"
        "Observation: Evaluate component interactions and check acceptance criteria alignment.\n"
        "Final Output: Return the required structured ArchitecturePlan schema.\n"
        "--- END REACT PATTERN ---\n"
    )

    @classmethod
    def get_backstory(cls, persona: PromptPersona) -> str:
        return cls._PERSONA_BACKSTORIES.get(
            persona,
            cls._PERSONA_BACKSTORIES[PromptPersona.PRAGMATIC_ARCHITECT],
        )

    @classmethod
    def build_architecture_prompt(
        cls,
        *,
        project_name: str,
        description: str,
        language: str,
        features: list[str],
        acceptance_criteria: list[str],
        config: PromptVarianceConfig | None = None,
    ) -> str:
        """Compose the complete prompt string with selected variances."""
        cfg = config or PromptVarianceConfig()

        base_prompt = (
            f"Create a concise architecture plan for this project.\n\n"
            f"Project: {project_name}\n"
            f"Description: {description}\n"
            f"Language: {language}\n"
            f"Features: {', '.join(features)}\n"
            f"Acceptance criteria: {'; '.join(acceptance_criteria) or 'Define suitable criteria.'}\n\n"
        )

        variance_additions = []

        if cfg.architecture == PromptArchitecture.FEW_SHOT:
            variance_additions.append(cls._FEW_SHOT_EXEMPLAR)
        elif cfg.architecture == PromptArchitecture.REACT:
            variance_additions.append(cls._REACT_INSTRUCTIONS)

        if cfg.persona == PromptPersona.DEFENSIVE_SECURITY_ARCHITECT or cfg.include_threat_modeling:
            variance_additions.append(
                "Security Directives:\n"
                "- Explicitly isolate data parsing boundaries.\n"
                "- Include at least 2 concrete security risks in the 'risks' field.\n"
            )

        variance_additions.append(
            f"Output requirements:\n"
            f"- Summary: maximum 80 words.\n"
            f"- Components: 3 to {cfg.max_components} entries.\n"
            f"- Proposed files: 3 to 6 paths.\n"
            f"- Implementation steps: 3 to 5 steps.\n"
            f"- Acceptance criteria: exactly 3 criteria.\n"
            f"- Risks: 1 to 3 entries.\n"
            f"- Return concise structured data matching the schema."
        )

        return base_prompt + "\n".join(variance_additions)

