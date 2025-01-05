# state_management.py
from enum import Enum, auto
from abc import ABC, abstractmethod
import json
from typing import Dict, List, Optional, Any
from collections import OrderedDict, deque
from game_objects import Case, Evidence, Witness, CaseType

class GamePhase(Enum):
    MAIN_MENU = auto()
    CASE_PREPARATION = auto()
    COURTROOM_PROCEEDINGS = auto()
    DELIBERATION = auto()
    VERDICT = auto()
    GAME_OVER = auto()

class Event:
    def __init__(self, name: str, data: Optional[Dict] = None):
        self.name = name
        self.data = data

class EventManager:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_name: str, listener):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(listener)

    def unsubscribe(self, event_name: str, listener):
        if event_name in self.listeners:
            self.listeners[event_name].remove(listener)

    def emit(self, event: Event):
        if event.name in self.listeners:
            for listener in self.listeners[event.name]:
                listener(event)

class GameStateObserver(ABC):
    @abstractmethod
    def on_state_change(self, new_state: GamePhase, context: Optional[Dict]):
        pass

class GameState:
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.observers = []
        self.current_phase = GamePhase.MAIN_MENU
        self.history = []
        self.active_case = None
        self.player_role = None
        self.player_reputation = 0
        self.completed_cases = []
        self.unlocked_cases = 1

    def add_observer(self, observer: GameStateObserver):
        self.observers.append(observer)

    def transition_to(self, new_phase: GamePhase, context: Optional[Dict] = None):
        self.history.append(self.current_phase)
        self.current_phase = new_phase
        self.event_manager.emit(Event("state_changed", {"new_phase": new_phase, "context": context}))

    def undo(self):
        if self.history:
            self.current_phase = self.history.pop()
            self.event_manager.emit(Event("state_changed", {"new_phase": self.current_phase, "context": None}))

class GameSerializer:
    def save_game_state(self, game_state: GameState, filename: str):
        state_dict = {
            'phase': game_state.current_phase.name,
            'reputation': game_state.player_reputation,
            'completed_cases': [self._serialize_case(case) for case in game_state.completed_cases],
            'current_case': self._serialize_case(game_state.active_case) if game_state.active_case else None,
            'unlocked_cases': game_state.unlocked_cases
        }
        with open(filename, 'w') as f:
            json.dump(state_dict, f)

    def load_game_state(self, filename: str, case_factory, witness_factory, evidence_factory, 
                       relationship_network, backstory_generator) -> GameState:
        with open(filename, 'r') as f:
            state_dict = json.load(f)
        
        game_state = GameState(EventManager())
        game_state.current_phase = GamePhase[state_dict['phase']]
        game_state.player_reputation = state_dict['reputation']
        game_state.completed_cases = [
            self._deserialize_case(
                case_dict, case_factory, witness_factory, evidence_factory,
                relationship_network, backstory_generator, case_factory.config
            )
            for case_dict in state_dict['completed_cases']
        ]
        
        if state_dict['current_case']:
            game_state.active_case = self._deserialize_case(
                state_dict['current_case'], case_factory, witness_factory,
                evidence_factory, relationship_network, backstory_generator,
                case_factory.config
            )
        
        game_state.unlocked_cases = state_dict.get('unlocked_cases', 1)
        return game_state

    def _serialize_case(self, case: Case) -> Dict:
        return {
            'title': case.title,
            'summary': case.summary,
            'case_type': case.case_type.value,
            'complexity': case.complexity,
            'num_witnesses': case.num_witnesses,
            'num_evidence': case.num_evidence,
            'evidence_templates': case.evidence_templates,
            'evidence_list': [self._serialize_evidence(evidence) for evidence in case.evidence_list],
            'witnesses': [self._serialize_witness(witness) for witness in case.witnesses],
            'case_context': case.case_context
        }

    def _deserialize_case(self, case_dict: Dict, case_factory, witness_factory, evidence_factory,
                         relationship_network, backstory_generator, config: Dict) -> Case:
        case = Case(
            title=case_dict['title'],
            summary=case_dict['summary'],
            case_type=CaseType(case_dict['case_type']),
            complexity=case_dict['complexity'],
            num_witnesses=case_dict['num_witnesses'],
            num_evidence=case_dict['num_evidence'],
            evidence_templates=case_dict['evidence_templates'],
            evidence_factory=evidence_factory,
            witness_factory=witness_factory,
            relationship_network=relationship_network,
            backstory_generator=backstory_generator,
            case_context=case_dict.get('case_context', {})
        )
        case.evidence_list = [self._deserialize_evidence(e_dict) for e_dict in case_dict['evidence_list']]
        case.witnesses = [self._deserialize_witness(w_dict, config) for w_dict in case_dict['witnesses']]
        return case

    def _serialize_evidence(self, evidence: Evidence) -> Dict:
        return {
            "type": evidence.type,
            "metadata": evidence.metadata,
            "authenticated": evidence.authenticated,
            "description": evidence.description
        }

    def _deserialize_evidence(self, evidence_dict: Dict) -> Evidence:
        evidence = Evidence(evidence_dict["type"], evidence_dict["metadata"])
        evidence.authenticated = evidence_dict["authenticated"]
        evidence.description = evidence_dict["description"]
        return evidence

    def _serialize_witness(self, witness: Witness) -> Dict:
        return {
            "name": witness.name,
            "occupation": witness.occupation,
            "personalities": witness.personalities,
            "relationship": witness.relationship,
            "backstory": witness.backstory,
            "stress": witness.stress,
            "testimony": list(witness.testimony.items()),
            "memory": list(witness.memory),
            "base_stress": witness.base_stress,
            "hidden_motive": witness.hidden_motive
        }

    def _deserialize_witness(self, witness_dict: Dict, config: Dict) -> Witness:
        witness = Witness(
            name=witness_dict["name"],
            occupation=witness_dict["occupation"],
            personalities=witness_dict["personalities"],
            relationship=witness_dict["relationship"],
            backstory=witness_dict["backstory"],
            base_stress=witness_dict["base_stress"],
            hidden_motive=witness_dict["hidden_motive"],
            config=config
        )
        witness.stress = witness_dict["stress"]
        witness.testimony = OrderedDict(witness_dict["testimony"])
        witness.memory = deque(witness_dict["memory"], maxlen=20)
        return witness