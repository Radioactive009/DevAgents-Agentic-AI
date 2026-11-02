"""
Google ADK Architecture Agent.

Implements the system architecture design agent using Google Agent Development Kit
(google-adk) and LiteLLM connecting to Groq. Integrates with the prompt variance
engine and outputs structured ArchitecturePlan Pydantic models.
"""

import json
import os
import re
from typing import Any, Callable

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
import litellm

from src.models import ArchitecturePlan, ProjectRequest
from src.prompts.variance_manager import (
    PromptPersona,
    PromptVarianceConfig,
    PromptVarianceManager,
)

load_dotenv(override=True)


def create_adk_architecture_agent(
    config: PromptVarianceConfig | None = None,
    before_callback: Callable[[Any], None] | None = None,
    after_callback: Callable[[Any], None] | None = None,
) -> Agent:
    """Instantiate a Google ADK Agent configured for architecture design."""
    cfg = config or PromptVarianceConfig()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Check your .env file.")

    llm = LiteLlm(
        model="groq/qwen/qwen3.8-27b",
        api_key=api_key,
        temperature=0.1,
        max_tokens=1200,
    )

    backstory = PromptVarianceManager.get_backstory(cfg.persona)

    agent = Agent(
        name="adk_software_architect",
        description="Google ADK Software Architect creating structured project plans.",
        instruction=(
            f"{backstory}\n\n"
            "Analyze project requirements and generate an ArchitecturePlan matching the exact schema. "
            "Return valid JSON adhering to the ArchitecturePlan model."
        ),
        model=llm,
        output_schema=ArchitecturePlan,
        before_agent_callback=before_callback,
        after_agent_callback=after_callback,
    )

    return agent


def generate_adk_architecture(
    request: ProjectRequest,
    config: PromptVarianceConfig | None = None,
    callback_listener: Any | None = None,
) -> ArchitecturePlan:
    """Generate an ArchitecturePlan using the Google ADK Agent."""
    cfg = config or PromptVarianceConfig()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Check your .env file.")

    prompt = PromptVarianceManager.build_architecture_prompt(
        project_name=request.project_name,
        description=request.description,
        language=request.language,
        features=request.features,
        acceptance_criteria=request.acceptance_criteria,
        config=cfg,
    )

    schema_instruction = (
        "\nIMPORTANT: Your response MUST be a single raw JSON object matching this schema:\n"
        "{\n"
        '  "project_name": string,\n'
        '  "summary": string,\n'
        '  "components": [string],\n'
        '  "proposed_files": [string],\n'
        '  "implementation_steps": [string],\n'
        '  "acceptance_criteria": [string],\n'
        '  "risks": [string]\n'
        "}\nDo not include code fences or conversational prose."
    )

    full_prompt = prompt + schema_instruction

    if callback_listener and hasattr(callback_listener, "before_agent"):
        callback_listener.before_agent("adk_software_architect", full_prompt)

    # Use litellm with Groq
    response = litellm.completion(
        model="groq/qwen/qwen3.8-27b",
        messages=[
            {
                "role": "system",
                "content": (
                    f"{PromptVarianceManager.get_backstory(cfg.persona)}\n"
                    "Always output strictly valid JSON matching ArchitecturePlan."
                ),
            },
            {"role": "user", "content": full_prompt},
        ],
        temperature=0.1,
        max_tokens=1200,
        api_key=api_key,
    )

    raw_text = response.choices[0].message.content.strip()

    # Strip code fences if present
    cleaned_json = raw_text
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        cleaned_json = match.group(1)
    else:
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            cleaned_json = json_match.group(0)

    try:
        data = json.loads(cleaned_json)
        # Ensure project_name matches request
        if "project_name" not in data or not data["project_name"]:
            data["project_name"] = request.project_name
        plan = ArchitecturePlan.model_validate(data)
    except Exception as err:
        raise ValueError(
            f"Failed to parse ADK architecture response into ArchitecturePlan: {err}\nRaw text: {raw_text[:300]}"
        ) from err

    if callback_listener and hasattr(callback_listener, "after_agent"):
        callback_listener.after_agent("adk_software_architect", plan)

    return plan

