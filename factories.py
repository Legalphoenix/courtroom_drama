# factories.py
import json
import os
import random
from typing import Dict, List, Tuple
from game_objects import Case, CaseType, Evidence, Witness

__all__ = ['CaseFactory', 'EvidenceFactory', 'WitnessFactory', 'RelationshipNetwork', 'BackstoryGenerator']

class EvidenceBuilder:
    def __init__(self, case_context: Dict):
        self.case_context = case_context
        self.evidence = None

    def set_base_type(self, evidence_type: str):
        self.evidence = Evidence(type=evidence_type, metadata={})
        return self

    def add_metadata(self, metadata: Dict):
        if self.evidence:
            self.evidence.metadata = metadata
        return self

    def generate_description(self):
        if not self.evidence:
            raise ValueError("Evidence type not set.")
        if self.evidence.type == "Digital":
            self.evidence.description = f"Digital evidence: {self.evidence.metadata['subtype']} related to the {self.case_context['type']} case."
        elif self.evidence.type == "Physical":
            self.evidence.description = f"Physical evidence: {self.evidence.metadata['subtype']} found at the scene."
        elif self.evidence.type == "Testimonial":
            self.evidence.description = f"Testimonial evidence: {self.evidence.metadata['subtype']} from a witness."
        else:
            self.evidence.description = f"Evidence relating to {self.case_context['type']} case."
        return self

    def authenticate_evidence(self):
        if not self.evidence:
            raise ValueError("Evidence not created yet.")
        difficulty_modifiers = self.case_context.get("difficulty_modifiers", {})
        authentication_modifier = difficulty_modifiers.get("evidence_authentication", 1.0)
        
        authentication_roll = random.uniform(0.0, 1.0)
        if authentication_roll < (0.7 * authentication_modifier):
            self.evidence.authenticated = True
        else:
            self.evidence.authenticated = False
        return self

    def build(self) -> Evidence:
        if not self.evidence:
            raise ValueError("Evidence not fully built.")
        return self.evidence

class EvidenceFactory:
    def __init__(self, config: Dict):
        self.config = config
        with open(config["template_paths"]["evidence_templates"], "r") as f:
            self.templates = json.load(f)["templates"]

    def generate_evidence(self, num_evidence: int, evidence_templates: List[str], case_context: Dict) -> List[Evidence]:
        generated_evidence = []
        available_templates = [t for t in self.templates if t["name"] in evidence_templates]

        if len(available_templates) < num_evidence:
            selected_templates = available_templates * (num_evidence // len(available_templates))
            selected_templates += random.sample(available_templates, num_evidence % len(available_templates))
        else:
            selected_templates = random.sample(available_templates, num_evidence)

        for template in selected_templates:
            builder = EvidenceBuilder(case_context)
            evidence = (builder
                      .set_base_type(template["type"])
                      .add_metadata({
                          "subtype": template["subtype"],
                          "description": template["description"],
                          "impact_metric": template["impact_metric"],
                          "synergy": template.get("synergy", [])
                      })
                      .generate_description()
                      .authenticate_evidence()
                      .build())
            generated_evidence.append(evidence)
        return generated_evidence


class WitnessFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.template_file = config["template_paths"]["witness_templates"]
        self.templates = self.load_templates()
        self.names = self.load_names()

    def load_templates(self) -> List[Dict]:
        with open(self.template_file, "r") as f:
            data = json.load(f)
        return data["templates"]

    def load_names(self) -> Dict:
        with open("names.json", "r") as f:
            return json.load(f)

    def create_witness(self, case_context: Dict, relationship: str, backstory_generator) -> Witness:
        personalities, base_stress = self.generate_personality()
        backstory = backstory_generator.generate(case_context["type"], case_context["witness_data"])
        name = self.generate_witness_name()
        hidden_motive = random.choice([
            "Financial struggles", "Personal grudges", "Desire for recognition",
            "Protecting someone", "Fear of reprisal"
        ])
        
        return Witness(
            name=name,
            occupation=case_context["witness_occupation"],
            personalities=personalities,
            relationship=relationship,
            backstory=backstory,
            base_stress=base_stress,
            hidden_motive=hidden_motive,
            config=self.config  # Make sure to pass config
        )

    def generate_personality(self) -> Tuple[List[str], int]:
        template = random.choice(self.templates)
        return template["personalities"], template["base_stress"]

    def generate_witness_name(self) -> str:
        first_name = random.choice(self.names["first_names"])
        last_name = random.choice(self.names["last_names"])
        return f"{first_name} {last_name}"

class CaseFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.template_file = config["template_paths"]["case_templates"]
        self.templates = self.load_templates()
        self.evidence_factory = EvidenceFactory(config)
        self.witness_factory = WitnessFactory(config)
        self.relationship_network = RelationshipNetwork()
        self.backstory_generator = BackstoryGenerator()

    def load_templates(self) -> List[Dict]:
        if not os.path.exists(self.template_file):
            raise FileNotFoundError(f"Case template file not found: {self.template_file}")
        with open(self.template_file, "r") as f:
            data = json.load(f)
        return data["templates"]

    def generate_case(self, player_level: int, previous_cases: List[str]) -> Case:
        suitable_templates = [t for t in self.templates if t["complexity"] <= player_level]
        if not suitable_templates:
            suitable_templates = self.templates
        
        template = random.choice(suitable_templates)
        case_type = CaseType(template["type"])
        
        witness_data = {
            "name": "",
            "company": "TechCorp",
            "years": random.randint(2, 10),
            "role": random.choice(template.get("witness_data", {}).get("possible_roles", ["Employee"])),
            "achievement": random.choice(template.get("witness_data", {}).get("possible_achievements", ["worked diligently"])),
            "suspicious_activity": random.choice(template.get("witness_data", {}).get("possible_suspicious_activities", ["nothing unusual"])),
            "responsibility": random.choice(template.get("witness_data", {}).get("possible_responsibilities", ["general duties"])),
            "security_record": random.choice(template.get("witness_data", {}).get("possible_security_records", ["no prior issues"]))
        }

        case_context = {
            "type": case_type.value,
            "complexity": template["complexity"],
            "witnesses": template["num_witnesses"],
            "witness_occupation": "Senior Employee at TechCorp",
            "witness_data": witness_data,
            "case_specific_traits": template.get("case_specific_traits", {}),
            "difficulty_modifiers": template.get("difficulty_modifiers", {}),
            "special_conditions": template.get("special_conditions", []),
        }

        return Case(
            title=f"{template['title_prefix']}{template['title_suffix']}",
            summary=template["summary"],
            case_type=case_type,
            complexity=template["complexity"],
            num_witnesses=template["num_witnesses"],
            num_evidence=template["num_evidence"],
            evidence_templates=template["evidence_templates"],
            evidence_factory=self.evidence_factory,
            witness_factory=self.witness_factory,
            relationship_network=self.relationship_network,
            backstory_generator=self.backstory_generator,
            case_context=case_context
        )

class RelationshipNetwork:
    def generate_relationships(self, num_witnesses: int) -> List[Tuple[int, str]]:
        relationships = []
        for i in range(num_witnesses):
            relationship = random.choice([
                "Colleague", "Supervisor", "Subordinate", "Client",
                "Vendor", "External Auditor", "Security Personnel"
            ])
            relationships.append((i, relationship))
        return relationships

class BackstoryGenerator:
    def generate(self, case_type: str, witness_data: Dict) -> str:
        """Generate a backstory for a witness based on case type and witness data."""
        template = (
            f"{witness_data['name']} has been with {witness_data['company']} "
            f"for {witness_data['years']} years as a {witness_data['role']}. "
            f"During their tenure, they {witness_data['achievement']}. "
            f"Their responsibilities included {witness_data['responsibility']}. "
            f"When questioned about suspicious activities, {witness_data['suspicious_activity']}. "
            f"Their security record shows {witness_data['security_record']}."
        )
        return template

