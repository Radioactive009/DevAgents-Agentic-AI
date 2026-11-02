"""Unit tests for Google ADK Architecture Agent."""
import unittest
from unittest.mock import MagicMock, patch

from google.adk import Agent
from src.adk_architecture_agent import (
    create_adk_architecture_agent,
    generate_adk_architecture,
)
from src.models import ArchitecturePlan, ProjectRequest
from src.prompts.variance_manager import (
    PromptArchitecture,
    PromptPersona,
    PromptVarianceConfig,
)


class TestAdkArchitectureAgent(unittest.TestCase):
    def setUp(self):
        self.request = ProjectRequest(
            project_name="ADK Test App",
            description="Testing the Google ADK Architecture agent.",
            language="Python",
            features=["Feature 1"],
            acceptance_criteria=["Criteria 1"],
        )

    @patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test_mock_key_12345"})
    def test_create_adk_agent(self):
        config = PromptVarianceConfig(
            architecture=PromptArchitecture.REACT,
            persona=PromptPersona.DEFENSIVE_SECURITY_ARCHITECT,
        )
        agent = create_adk_architecture_agent(config=config)
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.name, "adk_software_architect")
        self.assertEqual(agent.output_schema, ArchitecturePlan)

    @patch("litellm.completion")
    @patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test_mock_key_12345"})
    def test_generate_adk_architecture_success(self, mock_completion):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=(
                        '{\n'
                        '  "project_name": "ADK Test App",\n'
                        '  "summary": "Concise ADK design",\n'
                        '  "components": ["RouteHandler", "Store", "Tests"],\n'
                        '  "proposed_files": ["app.py", "store.py", "tests/test_api.py"],\n'
                        '  "implementation_steps": ["Step 1", "Step 2", "Step 3"],\n'
                        '  "acceptance_criteria": ["Criteria 1", "Criteria 2", "Criteria 3"],\n'
                        '  "risks": ["Risk 1"]\n'
                        '}'
                    )
                )
            )
        ]
        mock_completion.return_value = mock_response

        plan = generate_adk_architecture(self.request)
        self.assertIsInstance(plan, ArchitecturePlan)
        self.assertEqual(plan.project_name, "ADK Test App")
        self.assertEqual(len(plan.components), 3)
        self.assertEqual(len(plan.proposed_files), 3)


if __name__ == "__main__":
    unittest.main()

