import unittest
from unittest.mock import patch, AsyncMock
from game_logic import Witness
from factories.relationship_network import RelationshipNetwork
from factories.backstory_generator import BackstoryGenerator
from factories.case_factory import CaseType
import asyncio
import json
import os

class MockAIResponse:
    def __init__(self):
        self.responses = {
            "default": "I don't recall that specific detail.",
            "stress_high": "I... I'm not sure I should say this, but...",
            "defensive": "I've already answered that question!",
            "nervous": "Uh, I... I don't know.",
            "calm": "Yes, I am calm and answering directly.",
            "aggressive": "Why are you asking me that again?",
            "evasive": "I think you should be asking someone else about that."
        }

    async def generate_response(self, messages):
        # Simulate different responses based on the content of the messages
        prompt_text = messages[-1]['parts'][0]
        if "stress level is 8" in prompt_text.lower():
            return self.responses["stress_high"]
        elif "Defensive" in prompt_text:
            return self.responses["defensive"]
        elif "Nervous" in prompt_text:
            return self.responses["nervous"]
        elif "Calm" in prompt_text:
            return self.responses["calm"]
        elif "Aggressive" in prompt_text:
            return self.responses["aggressive"]
        elif "Evasive" in prompt_text:
            return self.responses["evasive"]
        else:
            return self.responses["default"]
        
class TestAIResponse(unittest.TestCase):
    def setUp(self):
        # Create a dummy config for testing
        self.config = {
            "gemini_api_key": "dummy_key",
            "template_paths": {
                "witness_templates": "factories/witness_templates.json"
            }
        }

        # Create dummy template files if they don't exist
        if not os.path.exists("factories"):
            os.makedirs("factories")
        if not os.path.exists("factories/witness_templates.json"):
            with open("factories/witness_templates.json", "w") as f:
                json.dump({"templates": [{"name": "Test Witness", "personalities": ["Test"], "base_stress": 1}]}, f)
        if not os.path.exists("names.json"):
            with open("names.json", "w") as f:
                json.dump({"first_names": ["Test"], "last_names": ["Name"]}, f)

        self.relationship_network = RelationshipNetwork()
        self.backstory_generator = BackstoryGenerator()
        self.witness = Witness(
            name="Alex Martinez",
            occupation="Senior Accountant at TechCorp",
            personalities=["Calm", "Calculated"],
            relationship="Colleague of the defendant",
            backstory="I have worked at TechCorp for over five years and have always maintained a professional relationship with everyone.",
            base_stress = 3,
            hidden_motive = "None"
        )
        self.witness.ai_manager = MockAIResponse()

    def test_ai_response_consistency(self):
        async def run_test():
            question1 = "Where were you on June 1st?"
            response1 = await self.witness.respond(question1, "Neutral", None)
            question2 = "Did you say you were at home on June 1st?"
            response2 = await self.witness.respond(question2, "Neutral", None)
            self.assertIn("I don't recall that specific detail.", response1)
            self.assertIn("I don't recall that specific detail.", response2)

        asyncio.run(run_test())

    def test_ai_response_stress(self):
        async def run_test():
            self.witness.stress = 8
            question = "Is there something you're not telling us?"
            response = await self.witness.respond(question, "Aggressive", None)
            self.assertIn("I... I'm not sure I should say this, but...", response)

        asyncio.run(run_test())

    def test_ai_response_defensive(self):
        async def run_test():
            self.witness.personalities = ["Defensive"]
            question = "Can you repeat your previous statement?"
            response = await self.witness.respond(question, "Neutral", None)
            self.assertIn("I've already answered that question!", response)

        asyncio.run(run_test())

    def test_ai_response_nervous(self):
        async def run_test():
            self.witness.personalities = ["Nervous"]
            question = "What is your name?"
            response = await self.witness.respond(question, "Neutral", None)
            self.assertIn("Uh, I... I don't know.", response)

        asyncio.run(run_test())

    def test_ai_response_calm(self):
        async def run_test():
            self.witness.personalities = ["Calm"]
            question = "Are you feeling ok?"
            response = await self.witness.respond(question, "Neutral", None)
            self.assertIn("Yes, I am calm and answering directly.", response)

        asyncio.run(run_test())

    def test_ai_response_aggressive(self):
        async def run_test():
            self.witness.personalities = ["Aggressive"]
            question = "Did you do it?"
            response = await self.witness.respond(question, "Neutral", None)
            self.assertIn("Why are you asking me that again?", response)

        asyncio.run(run_test())

    def test_ai_response_evasive(self):
        async def run_test():
            self.witness.personalities = ["Evasive"]
            question = "Where were you on that day?"
            response = await self.witness.respond(question, "Neutral", None)
            self.assertIn("I think you should be asking someone else about that.", response)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
