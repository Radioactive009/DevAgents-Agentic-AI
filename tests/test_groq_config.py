
import os
import unittest

from dotenv import load_dotenv


class TestGroqConfiguration(unittest.TestCase):
    def test_groq_api_key_is_configured(self):
        load_dotenv(override=True)

        api_key = os.getenv("GROQ_API_KEY")

        self.assertIsNotNone(
            api_key,
            "GROQ_API_KEY is missing from your .env file.",
        )
        self.assertTrue(
            api_key.strip(),
            "GROQ_API_KEY is empty.",
        )

        print("Groq API key is configured.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
