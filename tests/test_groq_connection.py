
import os
import unittest

import httpx
from dotenv import load_dotenv


class TestGroqConnection(unittest.TestCase):
    def test_list_available_models(self):
        load_dotenv(override=True)

        api_key = os.getenv("GROQ_API_KEY")
        self.assertTrue(api_key, "GROQ_API_KEY is missing from .env")

        response = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )

        self.assertEqual(
            response.status_code,
            200,
            f"Groq API returned HTTP {response.status_code}. "
            "Check the API key and account access.",
        )

        models = response.json().get("data", [])
        self.assertTrue(models, "Groq returned no available models.")

        print("\nAvailable Groq model IDs:")
        for model in models:
            print("-", model["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
