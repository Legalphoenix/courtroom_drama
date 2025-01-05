# game_objects.py
from enum import Enum
from typing import Dict, List, Optional
from collections import OrderedDict, deque
import random
from prompt_manager import GamePromptManager
from ai_module import ChatGPT, PromptManager

class CaseType(Enum):
    WHITE_COLLAR = "white_collar"
    THEFT = "theft"

class Evidence:
    def __init__(self, type: str, metadata: Dict):
        self.type = type
        self.metadata = metadata
        self.authenticated = False
        self.description: str = ""

    def authenticate(self):
        self.authenticated = True
        print(f"Evidence '{self.metadata['description']}' has been authenticated.")
        return True

    def to_dict(self):
        return {
            "type": self.type,
            "metadata": self.metadata,
            "authenticated": self.authenticated,
            "description": self.description
        }

    @staticmethod
    def from_dict(data):
        evidence = Evidence(data["type"], data["metadata"])
        evidence.authenticated = data["authenticated"]
        evidence.description = data["description"]
        return evidence

    def calculate_impact(self, juror) -> float:
        base_impact = self.metadata['impact_metric']
        personality_multipliers = {
            "Analytical": {"Digital": 1.5, "Physical": 1.2, "Testimonial": 0.8},
            "Empathetic": {"Testimonial": 1.5, "Physical": 1.0, "Digital": 0.8},
            "Skeptical": {"Digital": 1.0, "Physical": 1.0, "Testimonial": 0.7},
            "DEFAULT": {"Digital": 1.0, "Physical": 1.0, "Testimonial": 1.0}
        }
        bias_modifiers = {
            "Favor Evidence-Based Arguments": {"Digital": 1.3, "Physical": 1.2, "Testimonial": 0.9},
            "Skeptical": {"Digital": 0.9, "Physical": 0.9, "Testimonial": 0.7},
            "Empathetic": {"Digital": 0.8, "Physical": 0.9, "Testimonial": 1.3},
            "DEFAULT": {"Digital": 1.0, "Physical": 1.0, "Testimonial": 1.0}
        }

        personality_multiplier = personality_multipliers.get(juror.personality, {}).get(self.type, personality_multipliers["DEFAULT"][self.type])
        bias_modifier = bias_modifiers.get(juror.bias, {}).get(self.type, bias_modifiers["DEFAULT"][self.type])

        return base_impact * personality_multiplier * bias_modifier

class Witness:
    def __init__(self, name: str, occupation: str, personalities: List[str], relationship: str,
                 backstory: str, base_stress: int, hidden_motive: str, config: Dict):
        self.name = name
        self.occupation = occupation
        self.personalities = personalities
        self.relationship = relationship
        self.backstory = backstory
        self.stress = base_stress
        self.base_stress = base_stress
        self.hidden_motive = hidden_motive
        self.testimony = OrderedDict()
        self.memory = deque(maxlen=20)
        self.ai_manager = ChatGPT(config)  # You'll need to pass config to Witness
        self.prompt_manager = GamePromptManager(config)

    async def respond(self, question: str, strategy: str, game: "Game") -> str:
        self.update_stress(strategy)
        case_context_string = f"The case is about {game.current_case.summary} "
        if game.current_case.case_context.get("case_specific_traits"):
            case_context_string += "Special traits of this case include: " + ", ".join(
                f"{k}: {v}" for k, v in game.current_case.case_context["case_specific_traits"].items()) + ". "
        if game.current_case.case_context.get("special_conditions"):
            case_context_string += "Special conditions for this case are: " + ", ".join(
                game.current_case.case_context["special_conditions"]) + ". "

        # Construct the messages list correctly here:
        messages = self.prompt_manager.generate_prompt(
            "witness_testimony",
            {
                "witness_name": self.name,
                "personality_traits": self.personalities,
                "stress": self.stress,
                "backstory": self.backstory,
                "relationship": self.relationship,
                "previous_testimony": self.get_previous_testimony(),
                "question": question,
                "case_context": case_context_string,
                "hidden_motive": self.hidden_motive
            }
        )

        print(f"Messages to be sent to AI: {messages}")

        response = await self.ai_manager.get_response(messages)

        if self.stress > 7 and random.random() < 0.3:
            response += f" (Thinking about hidden motive: {self.hidden_motive})"

        self.testimony[question] = response
        self.memory.append({"question": question, "response": response})

        return response

    def update_stress(self, strategy: str):
        stress_modifiers = {
            "Aggressive": {"Nervous": 3, "Defensive": 2, "Evasive": 2, "DEFAULT": 2},
            "Neutral": {"DEFAULT": 1},
            "Friendly": {"Suspicious": 1, "Evasive": -2, "DEFAULT": -1}
        }
        default_modifier = stress_modifiers.get(strategy, {}).get("DEFAULT", 0)
        personality_modifier = next((stress_modifiers[strategy].get(p, default_modifier)
                                  for p in self.personalities), default_modifier)
        self.stress = max(min(self.stress + personality_modifier, 10), 0)

    def get_previous_testimony(self) -> str:
        """Returns a string summarizing the witness's previous testimony."""
        if not self.testimony:
            return "No previous testimony."

        summary = ""
        for i, (question, answer) in enumerate(self.testimony.items()):
            summary += f"Question {i + 1}: {question}\nAnswer {i + 1}: {answer}\n"
        return summary



class Case:
    def __init__(self, title: str, summary: str, case_type: CaseType, complexity: int,
                 num_witnesses: int, num_evidence: int, evidence_templates: List[str],
                 evidence_factory, witness_factory, relationship_network,
                 backstory_generator, case_context: Dict):
        self.title = title
        self.summary = summary
        self.case_type = case_type
        self.complexity = complexity
        self.num_witnesses = num_witnesses
        self.num_evidence = num_evidence
        self.evidence_templates = evidence_templates
        self.evidence_list: List[Evidence] = []
        self.witnesses: List[Witness] = []
        self._evidence_factory = evidence_factory
        self._witness_factory = witness_factory
        self._relationship_network = relationship_network
        self._backstory_generator = backstory_generator
        self.case_context = case_context
        self.generate_case()

    def display_summary(self):
        """Display a summary of the case"""
        print(f"\nCase Summary:")
        print(f"Title: {self.title}")
        print(f"Type: {self.case_type.value}")
        print(f"Summary: {self.summary}")
        print(f"Complexity Level: {self.complexity}")
        print("\nEvidence Available:")
        self.list_evidence()
        print("\nWitnesses Available:")
        self.list_witnesses()

    def list_evidence(self):
        """List all available evidence"""
        for i, evidence in enumerate(self.evidence_list, 1):
            status = "✓" if evidence.authenticated else "✗"
            print(f"{i}. {evidence.metadata['description']} ({evidence.type}) {status}")

    def list_witnesses(self):
        """List all available witnesses"""
        for i, witness in enumerate(self.witnesses, 1):
            print(f"{i}. {witness.name} - {witness.occupation}")

    def generate_case(self):
        self.evidence_list = self._evidence_factory.generate_evidence(
            num_evidence=self.num_evidence,
            evidence_templates=self.evidence_templates,
            case_context=self.case_context
        )
        relationships = self._relationship_network.generate_relationships(self.num_witnesses)
        self.witnesses = []
        for i in range(self.num_witnesses):
            witness = self._witness_factory.create_witness(
                self.case_context, relationships[i][1], self._backstory_generator
            )
            self.witnesses.append(witness)
