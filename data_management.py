import json
import os
from datetime import datetime
import logging
from typing import Dict, List

class Logger:
    def __init__(self, config: Dict, filename="game_log.json", error_log="error_log.txt"):
        self.filename = filename
        self.error_log = error_log
        self.logs = self.load_logs()

        log_level = config.get("log_level", "INFO")
        self.setup_logging(log_level)

    def setup_logging(self, log_level: str):
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(self.filename),
                logging.StreamHandler()
            ]
        )

    def load_logs(self) -> List[Dict]:
        if not os.path.exists(self.filename):
            return []
        with open(self.filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.error("Error decoding JSON from log file. Returning empty list.")
                return []

    def log_event(self, event_type: str, details: str):
        event = {
            "type": event_type,
            "details": details,
            "timestamp": self.get_timestamp()
        }
        self.logs.append(event)
        self.save_logs()
        logging.info(f"{event_type}: {details}")

    def save_logs(self):
        with open(self.filename, "w") as f:
            json.dump(self.logs, f, indent=4)

    def log_error(self, error_message: str):
        logging.error(error_message)
        with open(self.error_log, "a") as f:
            f.write(f"[{self.get_timestamp()}] ERROR: {error_message}\n")

    def get_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def display_logs(self):
        for log in self.logs:
            print(f"[{log['timestamp']}] {log['type']}: {log['details']}")