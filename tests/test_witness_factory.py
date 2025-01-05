import unittest
from factories.witness_factory import WitnessFactory
from factories.relationship_network import RelationshipNetwork
from factories.backstory_generator import BackstoryGenerator
from factories.case_factory import CaseType
import json
import os

class TestWitnessFactory(unittest.TestCase):
    def setUp(self):
        # Create a dummy config for testing
        self.config = {
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

        self.factory = WitnessFactory(self.config)
        self.relationship_network = RelationshipNetwork()
        self.backstory_generator = BackstoryGenerator()

    def test_create_witness(self):
        case_context = {
            "type": CaseType.WHITE_COLLAR.value,
            "complexity": 3,
            "witnesses": 2,
            "witness_occupation": "Senior Employee at TechCorp",
            "witness_data": {}
        }
        relationship = "Colleague"
        witness = self.factory.create_witness(case_context, relationship, self.backstory_generator)
        self.assertIsNotNone(witness.name)
        self.assertIsInstance(witness.personalities, list)
        self.assertGreater(len(witness.backstory), 0)
        self.assertEqual(witness.relationship, relationship)
        self.assertIn(witness.relationship, ["Colleague", "Friend", "Rival", "Supervisor", "Subordinate", "Acquaintance"])

if __name__ == '__main__':
    unittest.main()
