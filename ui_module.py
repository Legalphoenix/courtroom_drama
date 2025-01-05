import tkinter as tk
from tkinter import messagebox, simpledialog
from game_logic import Game, GamePhase
from game_objects import Witness, Evidence
from data_management import Logger
from state_management import GameStateObserver, Event
import asyncio
from typing import Dict, List, Optional

class UIObserver(GameStateObserver):
    def __init__(self, ui: "GameUI"):
        self.ui = ui

    def on_state_change(self, new_state: GamePhase, context: Optional[Dict]):
        if new_state == GamePhase.CASE_PREPARATION:
            self.ui.update_evidence_board()
            self.ui.update_witness_stand()
        elif new_state == GamePhase.DELIBERATION:
            self.ui.update_jury_box()

class MainMenu:
    def __init__(self, master, config: Dict):
        self.master = master
        self.config = config
        master.title("Courtroom Drama: Interactive Legal Simulation")
        master.geometry("400x300")

        self.label = tk.Label(master, text="Welcome to Courtroom Drama!", font=("Helvetica", 16))
        self.label.pack(pady=30)

        self.start_button = tk.Button(master, text="Start Career Mode", width=20, command=self.start_career)
        self.start_button.pack(pady=10)

        self.load_button = tk.Button(master, text="Load Game", width=20, command=self.load_game)
        self.load_button.pack(pady=10)

        self.exit_button = tk.Button(master, text="Exit", width=20, command=master.quit)
        self.exit_button.pack(pady=10)

    def start_career(self):
        """Start career mode and handle async operations properly"""
        async def init_game(game_ui):
            await game_ui.game.start_career_mode()  # Initialize the first case

        self.master.destroy()
        root = tk.Tk()
        game_ui = GameUI(root, self.config)

        # Run the async initialization
        asyncio.run(init_game(game_ui))

        # Start the Tkinter main loop
        root.mainloop()

    def load_game(self):
        game = Game(self.config)
        game.load_game()
        if game.state.current_phase != GamePhase.MAIN_MENU:
            self.master.destroy()
            root = tk.Tk()
            game_ui = GameUI(root, self.config, existing_game=game)
            asyncio.run(game_ui.game.start_game())
            root.mainloop()
        else:
            messagebox.showinfo("Load Game", "No saved game found or error loading game.")

class GameUI:
    def __init__(self, master, config: Dict, existing_game: Optional[Game] = None):
        self.master = master
        self.config = config
        master.title("Courtroom Drama: Interactive Legal Simulation")
        master.geometry("1000x600")

        if existing_game:
            self.game = existing_game
        else:
            self.game = Game(config)
        self.ui_observer = UIObserver(self)
        self.game.state.add_observer(self.ui_observer)
        self.game.state.event_manager.subscribe("state_changed", self.on_state_change)

        self.evidence_board = tk.Frame(master, bd=2, relief=tk.RIDGE)
        self.evidence_board.place(x=10, y=10, width=240, height=580)

        self.witness_stand = tk.Frame(master, bd=2, relief=tk.RIDGE)
        self.witness_stand.place(x=260, y=10, width=240, height=580)

        self.jury_box = tk.Frame(master, bd=2, relief=tk.RIDGE)
        self.jury_box.place(x=510, y=10, width=240, height=580)

        self.player_desk = tk.Frame(master, bd=2, relief=tk.RIDGE)
        self.player_desk.place(x=760, y=10, width=230, height=580)

        self.populate_evidence_board()
        self.populate_witness_stand()
        self.populate_jury_box()
        self.populate_player_desk()

    def on_state_change(self, event: Event):
        new_state = event.data["new_phase"]
        if new_state == GamePhase.CASE_PREPARATION:
            self.update_evidence_board()
            self.update_witness_stand()
        elif new_state == GamePhase.DELIBERATION:
            self.update_jury_box()

    def populate_evidence_board(self):
        for widget in self.evidence_board.winfo_children():
            widget.destroy()
        tk.Label(self.evidence_board, text="Evidence Board", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.evidence_buttons = []
        if self.game.current_case:
          for evidence in self.game.current_case.evidence_list:
              status = "✅" if evidence.authenticated else "❌"
              btn_text = f"{evidence.description} ({evidence.type}) {status}"
              btn = tk.Button(self.evidence_board, text=btn_text, wraplength=220, justify="left",
                              command=lambda e=evidence: self.present_evidence(e))
              btn.pack(pady=2, fill='x')
              self.evidence_buttons.append(btn)

    def populate_witness_stand(self):
        for widget in self.witness_stand.winfo_children():
            widget.destroy()
        tk.Label(self.witness_stand, text="Witness Stand", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.witness_buttons = []
        if self.game.current_case:
          for witness in self.game.current_case.witnesses:
              btn = tk.Button(self.witness_stand, text=witness.name, wraplength=220, justify="left",
                              command=lambda w=witness: self.examine_witness(w))
              btn.pack(pady=2, fill='x')
              self.witness_buttons.append(btn)

    def populate_jury_box(self):
        for widget in self.jury_box.winfo_children():
            widget.destroy()
        tk.Label(self.jury_box, text="Jury Box", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.juror_labels = []
        for juror in self.game.jury.jurors:
            sentiment_label = self.game.jury.get_sentiment_label(juror.sentiment)
            label_text = f"Juror #{juror.id}: {sentiment_label} ({juror.sentiment})"
            label = tk.Label(self.jury_box, text=label_text, bd=1, relief=tk.SOLID, anchor="w")
            label.pack(pady=2, fill='x')
            self.juror_labels.append(label)

    def populate_player_desk(self):
        for widget in self.player_desk.winfo_children():
            widget.destroy()
        tk.Label(self.player_desk, text="Your Desk", font=("Helvetica", 12, "bold")).pack(pady=5)
        self.opening_btn = tk.Button(self.player_desk, text="Make Opening Statement", width=25, command=self.make_opening_statement)
        self.opening_btn.pack(pady=10)

        self.closing_btn = tk.Button(self.player_desk, text="Make Closing Argument", width=25, command=self.make_closing_argument)
        self.closing_btn.pack(pady=10)

        self.log_btn = tk.Button(self.player_desk, text="View Logs", width=25, command=self.view_logs)
        self.log_btn.pack(pady=10)

        self.save_button = tk.Button(self.player_desk, text="Save Game", width=25, command=self.game.save_game)
        self.save_button.pack(pady=10)

    def present_evidence(self, evidence: Evidence):
        if not evidence.authenticated:
            messagebox.showwarning("Evidence Authentication", "This evidence has not been authenticated.")
            return
        messagebox.showinfo("Present Evidence", f"You have presented {evidence.description}.")
        # self.game.jury.assess_case(evidence.metadata['impact_metric'])
        self.game.jury.assess_case(evidence, self.game.current_case.case_context)
        self.update_juror_sentiments()
        self.game.log_event("Evidence Presented", evidence.description)
        idx = self.game.current_case.evidence_list.index(evidence)
        self.evidence_buttons[idx].config(bg="lightgreen")

    def examine_witness(self, witness: Witness):
        exam_window = tk.Toplevel(self.master)
        exam_window.title(f"Examining Witness: {witness.name}")
        exam_window.geometry("600x500")

        tk.Label(exam_window, text=f"Examining Witness: {witness.name}", font=("Helvetica", 14, "bold")).pack(pady=10)
        tk.Label(exam_window, text=f"Occupation: {witness.occupation}").pack(pady=5)
        traits = " + ".join(witness.personalities)
        tk.Label(exam_window, text=f"Personality Traits: {traits}").pack(pady=5)
        tk.Label(exam_window, text=f"Relationship: {witness.relationship}").pack(pady=5)
        stress_label = tk.Label(exam_window, text=f"Stress Level: {witness.stress}/10")
        stress_label.pack(pady=5)
        tk.Label(exam_window, text=f"Backstory: {witness.backstory}").pack(pady=5)

        tk.Label(exam_window, text="Questioning Phase:", font=("Helvetica", 12, "bold")).pack(pady=10)

        approach_frame = tk.Frame(exam_window)
        approach_frame.pack(pady=5)
        tk.Label(approach_frame, text="Choose your questioning approach:").pack(side="left", padx=5)
        approach_var = tk.StringVar(value="Neutral")
        for approach in ["Friendly", "Neutral", "Aggressive"]:
            tk.Radiobutton(approach_frame, text=approach, variable=approach_var, value=approach).pack(side="left")

        question_frame = tk.Frame(exam_window)
        question_frame.pack(pady=10)
        tk.Label(question_frame, text="Enter your question:").pack(side="left", padx=5)
        question_entry = tk.Entry(question_frame, width=50)
        question_entry.pack(side="left", padx=5)

        def submit_question():
            question = question_entry.get().strip()
            if not question:
                messagebox.showwarning("Input Error", "Please enter a question.")
                return
            strategy = approach_var.get()
            context = self.game.get_context()
            async def question_task():
                response = await witness.respond(question, strategy, self.game)
                print(f"Question: {question}\nResponse: {response}\n")
                response_text.config(state='normal')
                response_text.insert(tk.END, f"Q: {question}\nA: {response}\n\n")
                response_text.config(state='disabled')
                stress_label.config(text=f"Stress Level: {witness.stress}/10")
                question_entry.delete(0, tk.END)
                # self.game.jury.assess_case(impact)
                self.update_juror_sentiments()
                self.game.log_event("Witness Response", f"Q: {question} | A: {response}")
            asyncio.run(question_task())

        submit_btn = tk.Button(question_frame, text="Submit", command=submit_question)
        submit_btn.pack(side="left", padx=5)

        response_text = tk.Text(exam_window, wrap="word", height=15, width=70, state='disabled')
        response_text.pack(pady=10)

        def raise_objection():
            objection_window = tk.Toplevel(exam_window)
            objection_window.title("Raise Objection")
            tk.Label(objection_window, text="Choose objection type:").pack(pady=5)

            objection_var = tk.StringVar(value="Relevance")
            objection_types = ["Relevance", "Leading", "Hearsay", "Speculation"]
            for obj_type in objection_types:
                tk.Radiobutton(objection_window, text=obj_type, variable=objection_var, value=obj_type).pack(anchor="w")

            def confirm_objection():
                selected_objection = objection_var.get()
                self.game.log_event("Player Objection", selected_objection)
                ruling = self.game.judge_ruling(selected_objection, question_entry.get()) # Pass the question to judge_ruling
                messagebox.showinfo("Objection Ruling", f"Judge Ruling: {ruling}")
                if ruling == "Sustained":
                    self.game.jury.assess_case(1)
                else:
                    self.game.jury.assess_case(-1)
                self.update_juror_sentiments()
                objection_window.destroy()

            tk.Button(objection_window, text="Confirm", command=confirm_objection).pack(pady=5)

        objection_btn = tk.Button(exam_window, text="Raise Objection", command=raise_objection)
        objection_btn.pack(pady=5)

    def make_opening_statement(self):
        try:
            if not self.game.current_case:
                messagebox.showerror("Error", "No active case. Please start a new case first.")
                return

            if not self.game.role:
                role = self.choose_role()  # Make sure to implement this method
                if not role:
                    return

            # Get strategy from player
            strategy = simpledialog.askstring(
                "Opening Statement Strategy",
                "Enter your strategy (e.g., 'Focus on financial discrepancies'):"
            )
            if strategy is None:
                return  # User cancelled

            context = self.game.get_context()
            context["strategy"] = strategy
            context["statement_type"] = "opening"
            context["role"] = self.game.role
            context["case_type"] = self.game.current_case.case_type.value


            async def generate_statement_task():
                # Correctly pass "opening_statement" as the prompt type
                messages = self.game.prompt_manager.generate_prompt("opening_statement", context)
                statement = await self.game.ai_manager.get_response(messages)

                # Update UI to show the generated statement
                statement_window = tk.Toplevel(self.master)
                statement_window.title("Opening Statement")
                text_widget = tk.Text(statement_window, wrap='word', height=15, width=70)
                text_widget.pack(expand=True, fill='both')
                text_widget.insert(tk.END, statement)
                text_widget.config(state='disabled')

                # Log and assess impact
                self.game.log_event("Opening Statement", statement)
                impact = random.randint(1, 2)
                self.update_juror_sentiments()

            asyncio.run(generate_statement_task())

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.game.logger.log_error(f"Error in opening statement: {str(e)}")

    def choose_role(self):
        """Let player choose their role"""
        role_window = tk.Toplevel(self.master)
        role_window.title("Choose Your Role")
        role_window.geometry("300x150")

        selected_role = tk.StringVar()

        tk.Label(role_window, text="Choose Your Role:").pack(pady=10)
        tk.Radiobutton(role_window, text="Prosecution", variable=selected_role, value="Prosecution").pack()
        tk.Radiobutton(role_window, text="Defense", variable=selected_role, value="Defense").pack()

        def confirm_role():
            self.game.role = selected_role.get()
            role_window.destroy()

        tk.Button(role_window, text="Confirm", command=confirm_role).pack(pady=10)

        role_window.wait_window()  # Wait for window to close
        return self.game.role

    def make_closing_argument(self):
        # Placeholder for getting strategy from player
        strategy = simpledialog.askstring("Closing Argument Strategy", "Enter your strategy (e.g., 'Emphasize reasonable doubt'):")
        if strategy is None:
            return  # User cancelled

        context = self.game.get_context()
        context["strategy"] = strategy
        context["statement_type"] = "closing"

        async def generate_statement_task():
            messages = [{"role": "user", "parts": [self.game.prompt_manager.generate_prompt("closing_statement", context)[0]["parts"][0]]}]
            statement = await self.game.ai_manager.get_response(messages)

            # Update UI to show the generated statement
            statement_window = tk.Toplevel(self.master)
            statement_window.title("Closing Statement")
            text_widget = tk.Text(statement_window, wrap='word', height=15, width=70)
            text_widget.pack(expand=True, fill='both')
            text_widget.insert(tk.END, statement)
            text_widget.config(state='disabled')

            # Log and assess impact
            self.game.log_event("Closing Statement", statement)
            impact = random.randint(1, 2)
            # self.game.jury.assess_case(impact) # Assess impact if needed
            self.update_juror_sentiments()

        asyncio.run(generate_statement_task())

    def deliberation_and_verdict(self):
        messagebox.showinfo("Verdict", "Deliberation Phase is starting...")
        self.game.jury.deliberate_phase()
        self.update_juror_sentiments()
        verdict = self.game.jury.get_verdict()
        messagebox.showinfo("Verdict", f"The jury has reached a verdict: {verdict}")
        self.game.log_event("Verdict", verdict)
        if (self.game.role == "Prosecution" and verdict == "Guilty") or (self.game.role == "Defense" and verdict == "Not Guilty"):
            messagebox.showinfo("Outcome", "Congratulations! You have won the case.")
            self.game.reputation += 10
            self.game.log_event("Case Outcome", "Victory")
        else:
            messagebox.showinfo("Outcome", "The opposing side has won the case.")
            self.game.reputation -= 5
            self.game.log_event("Case Outcome", "Defeat")
        self.game.next_case()

    def update_juror_sentiments(self):
        for idx, juror in enumerate(self.game.jury.jurors):
            sentiment_label = self.game.jury.get_sentiment_label(juror.sentiment)
            label_text = f"Juror #{juror.id}: {sentiment_label} ({juror.sentiment})"
            self.juror_labels[idx].config(text=label_text)

    def view_logs(self):
        logs = self.game.logger.logs
        log_text = ""
        for log in logs:
            log_text += f"[{log['timestamp']}] {log['type']}: {log['details']}\n"
        log_window = tk.Toplevel(self.master)
        log_window.title("Game Logs")
        log_window.geometry("600x400")
        text_widget = tk.Text(log_window, wrap='word', state='disabled')
        text_widget.pack(expand=True, fill='both')
        text_widget.config(state='normal')
        text_widget.insert(tk.END, log_text)
        text_widget.config(state='disabled')

    def update_evidence_board(self):
        self.populate_evidence_board()

    def update_witness_stand(self):
        self.populate_witness_stand()

    def update_jury_box(self):
        self.populate_jury_box()
