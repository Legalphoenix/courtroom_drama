import unittest
from state_management import GameState, GamePhase, EventManager

class TestGameState(unittest.TestCase):
    def setUp(self):
        self.event_manager = EventManager()
        self.state = GameState(self.event_manager)

    def test_initial_state(self):
        self.assertEqual(self.state.current_phase, GamePhase.MAIN_MENU)

    def test_state_transition(self):
        self.state.transition_to(GamePhase.CASE_PREPARATION)
        self.assertEqual(self.state.current_phase, GamePhase.CASE_PREPARATION)
        self.state.undo()
        self.assertEqual(self.state.current_phase, GamePhase.MAIN_MENU)

    def test_multiple_state_transitions(self):
        self.state.transition_to(GamePhase.CASE_PREPARATION)
        self.state.transition_to(GamePhase.COURTROOM_PROCEEDINGS)
        self.state.transition_to(GamePhase.DELIBERATION)
        self.assertEqual(self.state.current_phase, GamePhase.DELIBERATION)
        self.state.undo()
        self.assertEqual(self.state.current_phase, GamePhase.COURTROOM_PROCEEDINGS)
        self.state.undo()
        self.assertEqual(self.state.current_phase, GamePhase.CASE_PREPARATION)

if __name__ == '__main__':
    unittest.main()
