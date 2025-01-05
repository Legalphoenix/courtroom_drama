import random
import os
import sys
import asyncio
from collections import OrderedDict, deque
from typing import Dict, List, Optional, Tuple
from prompt_manager import GamePromptManager
from ai_module import ChatGPT, PromptManager
from data_management import Logger
from state_management import GameState, GamePhase, EventManager, GameSerializer
from game_objects import Case, CaseType, Evidence, Witness
from factories import CaseFactory, EvidenceFactory, WitnessFactory, RelationshipNetwork, BackstoryGenerator
import logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler()])

class Juror:
    def __init__(self, id: int, personality: str, bias: str):
        self.id = id
        self.personality = personality
        self.bias = bias
        self.sentiment = 0
        self.memory = []
        self.persuasiveness = random.uniform(0.5, 1.5) # Base persuasiveness


    def evaluate_evidence(self, evidence: Evidence, case_context: Dict):
        impact = evidence.calculate_impact(self)

        # Modify impact based on special conditions
        if "media_attention" in case_context.get("special_conditions", []):
            if self.bias == "Favor Evidence-Based Arguments":
                impact *= 1.1  # Slightly increase impact for evidence-focused jurors
            elif self.bias == "Empathetic":
                impact *= 0.9 # Slightly decrease impact for empathetic jurors

        if "political_pressure" in case_context.get("special_conditions", []):
            if self.bias == "Skeptical":
                impact *= 1.1 # Slightly increase impact for skeptical jurors
            elif self.bias == "Empathetic":
                impact *= 0.9 # Slightly decrease impact for empathetic jurors

        self.sentiment += impact

    def deliberate(self, trial_events: List[Dict], all_jurors: List["Juror"]):
        for event in trial_events:
            if event['type'] == 'evidence_presented':
                self.evaluate_evidence(event['evidence'], event['case_context'])
            elif event['type'] == 'witness_testimony':
                self.sentiment += event['impact']

        # Influence from other jurors
        for other_juror in all_jurors:
            if self.id != other_juror.id:
                influence = (other_juror.persuasiveness - self.persuasiveness) * 0.5  # Max 0.5 change
                self.sentiment += influence

        self.sentiment = max(min(self.sentiment, 5), -5)

class Jury:
    def __init__(self, number_of_jurors: int = 5):
        self.jurors = []
        for i in range(1, number_of_jurors + 1):
            personality = random.choice(["Analytical", "Empathetic", "Skeptical"])
            bias = random.choice(["Favor Evidence-Based Arguments", "Skeptical", "Empathetic"])
            self.jurors.append(Juror(i, personality, bias))
        self.trial_events = []

    def assess_case(self, evidence: Evidence, case_context: Dict):
        for juror in self.jurors:
            juror.evaluate_evidence(evidence, case_context)
            self.trial_events.append({'type': 'evidence_presented', 'evidence': evidence, 'case_context': case_context, 'impact': evidence.calculate_impact(juror)})

    def deliberate_phase(self):
        for juror in self.jurors:
            juror.deliberate(self.trial_events, self.jurors)

    def get_verdict(self) -> str:
        total_sentiment = sum(juror.sentiment for juror in self.jurors)
        if total_sentiment > 0:
            return "Guilty"
        else:
            return "Not Guilty"

    def display_juror_states(self):
        for juror in self.jurors:
            sentiment_label = self.get_sentiment_label(juror.sentiment)
            print(f"Juror #{juror.id} ({juror.personality}, Bias: {juror.bias}) - Sentiment: {sentiment_label} ({juror.sentiment})")

    def get_sentiment_label(self, sentiment: int) -> str:
        if sentiment < 0:
            return "Negative"
        elif sentiment > 0:
            return "Positive"
        else:
            return "Neutral"

class Game:
    def __init__(self, config: Dict, jury: Optional[Jury] = None):
        print("Initializing Game...")
        print(f"Config in Game.__init__: {config}")  # Check config
        self.config = config
        self.event_manager = EventManager()
        self.state = GameState(self.event_manager)
        self.case_factory = CaseFactory(config)
        self.current_case: Optional[Case] = None
        self.role: Optional[str] = None
        self.selected_evidence: Dict[str, Evidence] = {}
        self.selected_witness_order: List[int] = []
        self.jury = jury or Jury()
        self.reputation = 0
        self.logger = Logger(config)
        self.serializer = GameSerializer()
        self.ai_manager = ChatGPT(config)
        print("Initializing PromptManager...")
        self.prompt_manager = GamePromptManager(config)  # Pass config
        print(f"PromptManager initialized: {self.prompt_manager}")  #
        print("Game initialization complete.")

    def log_event(self, event_type: str, details: str):
        self.logger.log_event(event_type, details)

    async def start_game(self):
        print("Welcome to Courtroom Drama: Interactive Legal Simulation\n")
        # Initialize first case immediately
        await self.start_career_mode()

    def main_menu(self):
        while True:
            print("\nMain Menu:")
            print("1. Start Career Mode")
            print("2. Continue Case")
            print("3. Load Game")
            print("4. Save Game")
            print("5. Exit")
            choice = input("Enter your choice: ")
            if choice == "1":
                asyncio.run(self.start_career_mode())
            elif choice == "2":
                self.continue_case()
            elif choice == "3":
                self.load_game()
            elif choice == "4":
                self.save_game()
            elif choice == "5":
                print("Thank you for playing Courtroom Drama. Goodbye!")
                self.logger.log_event("Game Exit", "User exited the game")
                sys.exit()
            else:
                print("Invalid choice. Please try again.")

    async def start_career_mode(self):
        """Initialize the career mode and first case"""
        print("\nCareer Mode Selected.\n")
        self.state.player_reputation = 0
        self.state.unlocked_cases = 1
        # Create the first case immediately
        self.current_case = self.case_factory.generate_case(
            player_level=1,
            previous_cases=[]
        )
        self.state.transition_to(GamePhase.CASE_PREPARATION)
        print(f"Starting Case {self.state.unlocked_cases}: {self.current_case.title}\n")
        self.current_case.display_summary()

    def get_context(self) -> Dict:
        """Get current game context with proper error handling"""
        if not self.current_case:
            raise ValueError("No active case. Please start a case before performing actions.")

        evidence_presented = [f"{evidence.type}: {evidence.description}"
                            for evidence in self.selected_evidence.values()]

        return {
            "current_case_title": self.current_case.title,
            "current_case_summary": self.current_case.summary,
            "case_type": self.current_case.case_type.value,  # Add this line
            "player_role": self.role or "Undecided",
            "role": self.role or "Undecided",  # Add this line too - some prompts use role instead of player_role
            "evidence_presented": ", ".join(evidence_presented) if evidence_presented else "No evidence presented yet.",
            "special_conditions": ", ".join(self.current_case.case_context.get("special_conditions", [])) or "None",
            "strategy": "",  # Add a default empty strategy
        }

    async def continue_case(self):
        if self.current_case:
            self.case_preparation()
            await self.courtroom_proceedings()
            self.deliberation_and_verdict()
        else:
            print("No ongoing case found. Please start a new career mode or load a saved game.")

    async def next_case(self):
        if self.state.unlocked_cases <= len(self.case_factory.templates):
            self.state.transition_to(GamePhase.CASE_PREPARATION)
            self.current_case = self.case_factory.generate_case(
                player_level=self.state.player_reputation // 10 + 1,
                previous_cases=self.state.completed_cases
            )
            print(f"Starting Case {self.state.unlocked_cases}: {self.current_case.title}\n")
            self.current_case.display_summary()
            self.choose_role()
            self.case_preparation()
            await self.courtroom_proceedings()
            self.deliberation_and_verdict()
            self.state.completed_cases.append(self.current_case)
            self.state.unlocked_cases += 1
        else:
            print("Congratulations! You have completed all available cases.")
            self.logger.log_event("Game Completion", "All cases completed")
            self.state.transition_to(GamePhase.GAME_OVER)
            sys.exit()

    def choose_role(self):
        while True:
            print("Choose Your Role:")
            print("1. Prosecution")
            print("2. Defense")
            choice = input("Enter your choice: ")

            if choice == "1":
                self.role = "Prosecution"
                print("You have chosen to be the Prosecution.\n")
                self.log_event("Role Selection", "Prosecution")
                break
            elif choice == "2":
                self.role = "Defense"
                print("You have chosen to be the Defense.\n")
                self.log_event("Role Selection", "Defense")
                break
            else:
                print("Invalid choice. Please try again.")

    def case_preparation(self):
        print("Case Preparation Phase:\n")
        self.current_case.list_evidence()
        while True:
            selected = input("Select up to two pieces of evidence to present (e.g., 1,3 or 'none'): ")
            if selected.lower() == 'none':
                self.selected_evidence = {}
                break

            indices = selected.split(",")
            self.selected_evidence = {}
            valid_selection = True
            for idx in indices:
                idx = idx.strip()
                if idx.isdigit() and 1 <= int(idx) <= len(self.current_case.evidence_list):
                    evidence = self.current_case.evidence_list[int(idx) - 1]
                    if evidence.authenticated:
                        self.selected_evidence[evidence.metadata['description']] = evidence
                        self.log_event("Evidence Selected", evidence.metadata['description'])
                    else:
                        print(f"Evidence '{evidence.metadata['description']}' is not authenticated.")
                        valid_selection = False
                else:
                    print(f"Invalid evidence selection: {idx}")
                    valid_selection = False
            if valid_selection:
                break

        print("\nWitness Information:")
        self.current_case.list_witnesses()
        while True:
            order = input("Choose the order to examine witnesses (e.g., 1,2 or 2,1): ")
            order_indices = order.split(",")
            valid = True
            temp_order = []
            for idx in order_indices:
                idx = idx.strip()
                if idx.isdigit() and 1 <= int(idx) <= len(self.current_case.witnesses):
                    temp_order.append(int(idx) - 1)
                else:
                    print(f"Invalid witness selection: {idx}")
                    valid = False
                    break
            if valid and len(temp_order) == len(self.current_case.witnesses):
                self.selected_witness_order = temp_order
                self.log_event("Witness Order Selection", self.selected_witness_order)
                break
            else:
                print("Invalid order selection. Please try again.")
        print("\nCase Preparation Complete.\n")
        self.log_event("Case Preparation Complete", "Selected evidence and witness order")

    async def courtroom_proceedings(self):
        print("Courtroom Proceedings:\n")
        await self.opening_statements()
        await self.examine_witnesses()
        self.closing_arguments()

    async def opening_statements(self):
        print("Opening Statements:\n")

        if not self.role:
            self.choose_role()  # Make sure role is selected

        logging.info(f"Current context for opening statement: {self.get_context()}")  # Debug logging

        try:
            context = self.get_context()
            context["strategy"] = "Focus on establishing key evidence and timeline of events"  # Default strategy

            messages = self.prompt_manager.generate_prompt("opening_statement", context)
            statement = await self.ai_manager.get_response(messages)

            print("\nYour Opening Statement:")
            print(statement)
            print("\n")

            self.log_event("Opening Statement", statement)
            impact = random.randint(1, 2)
            self.jury.trial_events.append({'type': 'opening_statement', 'impact': impact})

        except Exception as e:
            logging.error(f"Error generating opening statement: {e}")
            # Fallback to default statements if AI generation fails
            if self.role == "Prosecution":
                statements = [
                    "Ladies and gentlemen of the jury, today you will see undeniable evidence that Mr. Smith abused his position to siphon funds from TechCorp.",
                    "The prosecution will demonstrate how meticulous planning and opportunistic actions led to the financial discrepancies observed.",
                    "We are here to uncover the truth behind the alleged embezzlement and hold the responsible party accountable."
                ]
            else:
                statements = [
                    "Ladies and gentlemen, the defense will show that there is reasonable doubt regarding the allegations against my client.",
                    "We will demonstrate that the evidence is circumstantial and that Mr. Smith had no intention to defraud TechCorp.",
                    "Our goal is to ensure that justice is served by thoroughly examining the facts presented."
                ]

            for idx, stmt in enumerate(statements, 1):
                print(f"{idx}. {stmt}")

            while True:
                choice = input("Enter the number of your chosen opening statement: ")
                if choice.isdigit() and 1 <= int(choice) <= len(statements):
                    selected_statement = statements[int(choice) - 1]
                    print(f"\nYou selected: \"{selected_statement}\"\n")
                    self.log_event("Opening Statement", selected_statement)
                    impact = random.randint(1, 2)
                    break
                else:
                    print("Invalid choice. Please try again.")

    async def examine_witnesses(self):
        for witness_idx in self.selected_witness_order:
            witness = self.current_case.witnesses[witness_idx]
            print(f"Examining Witness: {witness.name}\n")
            print(f"Occupation: {witness.occupation}")
            traits = " + ".join(witness.personalities)
            print(f"Personality Traits: {traits}")
            print(f"Relationship: {witness.relationship}\n")
            print(f"Backstory: {witness.backstory}\n")
            print(f"Stress Level: {witness.stress}/10\n")

            # Choose questioning approach
            print("Choose your questioning approach:")
            print("1. Friendly")
            print("2. Neutral")
            print("3. Aggressive")
            while True:
                choice = input("Enter your choice: ")
                if choice == "1":
                    strategy = "Friendly"
                    break
                elif choice == "2":
                    strategy = "Neutral"
                    break
                elif choice == "3":
                    strategy = "Aggressive"
                    break
                else:
                    print("Invalid choice. Please try again.")
            print(f"\nYou have chosen a {strategy} approach.\n")
            self.log_event("Questioning Approach", strategy)

            # Simulate asking 3 questions
            for q_num in range(1, 4):
                print(f"Question {q_num}:")
                question = input("Enter your question: ")
                response = await witness.respond(question, strategy, self)
                print(f"Witness Response: {response}\n")
                self.log_event("Witness Response", f"Q: {question} | A: {response}")

                # Check for evidence synergy
                for desc, evidence in self.selected_evidence.items():
                    for other_desc, other_evidence in self.selected_evidence.items():
                        if desc != other_desc and evidence.metadata['synergy'] is not None and other_evidence.metadata['synergy'] is not None:
                            if other_evidence.type in evidence.metadata['synergy'] and evidence.type in other_evidence.metadata['synergy']:
                                print(f"Synergy between {evidence.type} and {other_evidence.type} activated!")
                                for juror in self.jury.jurors:
                                    juror.sentiment += 1 # Add extra sentiment for synergy

                impact = random.randint(-1, 2)
                self.jury.trial_events.append({'type': 'witness_testimony', 'impact': impact})

                objection = input("Do you want to raise an objection? (yes/no): ").lower()
                if objection == "yes":
                    self.raise_objection(witness, question)

                if random.random() < 0.3:
                    objection_type = random.choice(["Relevance", "Leading", "Hearsay", "Speculation"])
                    print(f"Opposing side raises an objection: {objection_type}")
                    ruling = self.judge_ruling(objection_type, question)
                    print(f"Judge Ruling: {ruling}\n")
                    if ruling == "Sustained":
                        for juror in self.jury.jurors:
                            juror.sentiment += 1
                    else:
                        for juror in self.jury.jurors:
                            juror.sentiment -= 1
                    self.log_event("Objection Ruling", ruling)

    def raise_objection(self, witness: Witness, question: str):
        print("Choose objection type:")
        objections = ["Relevance", "Leading", "Hearsay", "Speculation"]
        for idx, obj in enumerate(objections, 1):
            print(f"{idx}. {obj}")
        while True:
            choice = input("Enter the number of your objection: ")
            if choice.isdigit() and 1 <= int(choice) <= len(objections):
                objection_type = objections[int(choice) - 1]
                break
            else:
                print("Invalid choice. Please try again.")
        self.log_event("Player Objection", objection_type)
        ruling = self.judge_ruling(objection_type, question)
        print(f"Judge Ruling: {ruling}\n")
        if ruling == "Sustained":
            for juror in self.jury.jurors:
                juror.sentiment += 1
        else:
            for juror in self.jury.jurors:
                juror.sentiment -= 1
        self.log_event("Objection Ruling", ruling)

    def judge_ruling(self, objection_type: str, question: str) -> str:
        prompt_manager = PromptManager(self.config)  # Pass self.config
        prompt = prompt_manager.generate_prompt(
            "judge_ruling",
            {
                "case_type": self.current_case.case_type.value,
                "objection_type": objection_type,
                "question": question
            }
        )
        messages = [{"role": "user", "parts": [prompt]}]
        ruling = asyncio.run(self.ai_manager.generate_response(messages))
        # Extract ruling from AI response
        if "sustained" in ruling.lower():
            return "Sustained"
        elif "overruled" in ruling.lower():
            return "Overruled"
        else:
            return "Overruled"

    def closing_arguments(self):
        print("Closing Arguments:\n")
        if self.role == "Prosecution":
            arguments = [
                "Emphasize the financial records and their alignment with witness testimonies.",
                "Highlight inconsistencies in the defense's presentation of evidence.",
                "Appeal to the jury's sense of justice and corporate responsibility."
            ]
        else:
            arguments = [
                "Emphasize the reasonable doubt and lack of concrete evidence.",
                "Highlight the credibility issues with the prosecution's witnesses.",
                "Appeal to the jury's sense of fairness and the presumption of innocence."
            ]
        for idx, arg in enumerate(arguments, 1):
            print(f"{idx}. {arg}")
        while True:
            choice = input("Enter the number of your chosen closing argument: ")
            if choice.isdigit() and 1 <= int(choice) <= len(arguments):
                selected_argument = arguments[int(choice) - 1]
                print(f"\nYou selected: \"{selected_argument}\"\n")
                self.log_event("Closing Argument", selected_argument)
                impact = random.randint(2, 4)
                # self.jury.assess_case(impact) # Closing arguments don't use evidence directly
                break
            else:
                print("Invalid choice. Please try again.")

    def deliberation_and_verdict(self):
        print("Deliberation Phase:\n")
        for evidence_desc, evidence in self.selected_evidence.items():
          self.jury.assess_case(evidence, self.current_case.case_context)
        self.jury.deliberate_phase()
        print("Jurors are deliberating...\n")
        self.jury.display_juror_states()
        verdict = self.jury.get_verdict()
        print(f"\nVerdict: {verdict}\n")
        self.log_event("Verdict", verdict)
        if (self.role == "Prosecution" and verdict == "Guilty") or (self.role == "Defense" and verdict == "Not Guilty"):
            print("Congratulations! You have won the case.\n")
            self.reputation += 10
            self.log_event("Case Outcome", "Victory")
        else:
            print("The opposing side has won the case.\n")
            self.reputation -= 5
            self.log_event("Case Outcome", "Defeat")
        self.next_case()

    def get_context(self) -> Dict:
        evidence_presented = [f"{evidence.type}: {evidence.description}" for evidence in self.selected_evidence.values()]
        return {
            "current_case_title": self.current_case.title,
            "current_case_summary": self.current_case.summary,
            "player_role": self.role,
            "evidence_presented": ", ".join(evidence_presented) if evidence_presented else "No evidence presented yet.",
            "special_conditions": ", ".join(self.current_case.case_context.get("special_conditions", [])) or "None",
        }

    def save_game(self):
        filename = "save_game.json"
        self.serializer.save_game_state(
            game_state=self.state,
            filename=filename
        )
        print(f"Game state has been saved to {filename}.")
        self.log_event("Game Saved", "User saved the game.")

    def load_game(self):
        filename = "save_game.json"
        if not os.path.exists(filename):
            print("No saved game found.")
            return
        try:
            self.state = self.serializer.load_game_state(
                filename=filename,
                case_factory=self.case_factory,
                witness_factory=self.case_factory.witness_factory,
                evidence_factory=self.case_factory.evidence_factory,
                relationship_network=self.case_factory.relationship_network,
                backstory_generator=self.case_factory.backstory_generator
            )
            print("Game state has been loaded.")
            self.log_event("Game Loaded", "User loaded the game.")
            self.current_case = self.state.active_case
            self.reputation = self.state.player_reputation
            self.unlocked_cases = self.state.unlocked_cases
            self.completed_cases = self.state.completed_cases
        except Exception as e:
            print(f"Error loading game: {e}")
            self.logger.log_error(f"Error loading game: {e}")
