import tkinter as tk
from ui_module import MainMenu
import json

def main():
    with open("config.json", "r") as f:
        config = json.load(f)

    root = tk.Tk()
    main_menu = MainMenu(root, config)
    root.mainloop()

if __name__ == "__main__":
    main()
