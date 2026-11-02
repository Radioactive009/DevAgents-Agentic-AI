"""Unit tests for BlackboardMessaging and EventBusMessaging."""
import unittest
from uuid import uuid4

from src.messaging.blackboard_adapter import BlackboardMessaging
from src.messaging.event_bus import EventBusMessaging
from src.models import (
    ArchitecturePlan,
    DebugReport,
    ProjectRequest,
    TestResult,
)


class TestMessagingArchitectures(unittest.TestCase):
    def setUp(self):
        self.request = ProjectRequest(
            project_name="Test App",
            description="A test app for messaging validation.",
            language="Python",
            features=["Feature A"],
            acceptance_criteria=["Criterion 1"],
        )
        self.plan = ArchitecturePlan(
            project_name="Test App",
            summary="A short summary.",
            components=["Comp1", "Comp2", "Comp3"],
            proposed_files=["app.py", "models.py", "tests/test_api.py"],
            implementation_steps=["Step 1", "Step 2", "Step 3"],
            acceptance_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
            risks=["Risk 1"],
        )

    def test_blackboard_messaging_lifecycle(self):
        bb = BlackboardMessaging(task_id=str(uuid4()), request=self.request)
        received = []
        bb.subscribe("architecture.plan", lambda payload: received.append(payload))

        bb.publish("architecture.plan", self.plan)
        self.assertEqual(len(received), 1)
        self.assertEqual(bb.get_state().status, "coding")

        bb.publish("code.files", ["app.py", "models.py", "tests/test_api.py"])
        self.assertEqual(len(bb.get_state().code_files), 3)

    def test_event_bus_messaging_lifecycle(self):
        eb = EventBusMessaging(task_id=str(uuid4()), request=self.request)
        received = []
        eb.subscribe("architecture.plan", lambda payload: received.append(payload))

        eb.publish("architecture.plan", self.plan)
        self.assertEqual(len(received), 1)
        self.assertEqual(eb.get_state().status, "coding")
        self.assertEqual(len(eb.event_log), 1)

        eb.publish("code.files", ["app.py", "models.py"])
        self.assertEqual(len(eb.get_state().code_files), 2)
        self.assertEqual(len(eb.event_log), 2)


if __name__ == "__main__":
    unittest.main()

