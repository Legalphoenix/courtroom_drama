import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from game_logic import Game, Witness, Jury
from factories.relationship_network import RelationshipNetwork
from factories.backstory_generator import BackstoryGenerator
from factories.case_factory import CaseFactory, CaseType
from factories.evidence_factory import EvidenceFactory
import asyncio
import json
import os

class MockAIResponse:
    def __init__(self):
        self.responses = {
            "default": "I was at my desk preparing reports.",
            "stress_high": "I... I'm not sure I should say this, but...",
            "defensive": "I've already answered that question!",
            "nervous": "Uh, I... I don't know.",
            "calm": "Yes, I am calm and answering directly.",
            "aggressive": "Why are you asking me that again?",
            "evasive": "I think you should be asking someone else about that."
        }

    async def generate_response(self, messages):
        # Simulate different responses based on the content of the messages
        prompt_text = messages[-1]['parts'][0] # Access the prompt text correctly
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

class TestCourtSession(unittest.TestCase):
    def setUp(self):
        # Create a dummy config for testing
        self.config = {
            "gemini_api_key": "dummy_key",
            "template_paths": {
                "case_templates": "factories/case_templates.json",
                "witness_templates": "factories/witness_templates.json",
                "evidence_templates": "factories/evidence_templates.json"
            },
            "max_tokens": 300,
            "log_level": "INFO"
        }
        # Create dummy template files if they don't exist
        if not os.path.exists("factories"):
            os.makedirs("factories")
        if not os.path.exists("factories/case_templates.json"):
            with open("factories/case_templates.json", "w") as f:
                json.dump({"templates": [{"type": "white_collar", "title_prefix": "Test ", "title_suffix": " Case", "summary": "Test Summary", "evidence_templates": [], "num_witnesses": 2, "num_evidence": 2, "complexity": 1, "witness_data": {}, "case_specific_traits": {}, "difficulty_modifiers": {}, "special_conditions": []}]}, f)
        if not os.path.exists("factories/witness_templates.json"):
            with open("factories/witness_templates.json", "w") as f:
                json.dump({"templates": [{"name": "Test Witness", "personalities": ["Test"], "base_stress": 1}]}, f)
        if not os.path.exists("factories/evidence_templates.json"):
            with open("factories/evidence_templates.json", "w") as f:
                json.dump({"templates": [{"name": "Test Evidence", "type": "Test", "subtype": "Test", "description": "Test Description", "impact_metric": 1, "synergy": []}]}, f)
        if not os.path.exists("names.json"):
            with open("names.json", "w") as f:
                json.dump({"first_names": ["Test"], "last_names": ["Name"]}, f)

    @patch('ai_module.ChatGPT', new_callable=lambda: AsyncMock(spec=ChatGPT))
    def test_complete_trial_flow(self, mock_chat_gpt):
        # Mock the AI response for witness testimony
        mock_chat_gpt.return_value.get_response = AsyncMock(side_effect=MockAIResponse().generate_response)
        mock_jury = MagicMock(spec=Jury)
        mock_jury.get_verdict.return_value = "Guilty"
        game = Game(self.config, jury=mock_jury)

        game.current_case = game.case_factory.generate_case(
            player_level=1,
            previous_cases=[]
        )
        game.role = "Prosecution"
        game.selected_evidence = {e.metadata['description']: e for e in game.current_case.evidence_list[:2]}
        game.selected_witness_order = [0, 1]

        async def run_test():
            with patch('builtins.input', side_effect=["1", "1", "1", "Where were you on June 1st?", "no", "no", "no", "1"]):
                game.opening_statements()
                await game.examine_witnesses()
                game.closing_arguments()
                game.deliberation_and_verdict()

            self.assertTrue(mock_chat_gpt.called)

            mock_jury.assess_case.assert_called()
            mock_jury.deliberate_phase.assert_called()
            mock_jury.get_verdict.assert_called()

            if game.role == "Prosecution":
              self.assertIn(game.reputation, [10])
            if game.role == "Defense":
              self.assertIn(game.reputation, [-5])

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()