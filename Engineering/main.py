# ============================================================
# main.py — Engineering
# Point d'entrée de l'application.
# ============================================================

import sys
import traceback

import customtkinter as ctk

import config
from ui.app import EngineeringApp


def main():
    # Thème global CustomTkinter
    ctk.set_appearance_mode(config.THEME_MODE)
    ctk.set_default_color_theme(config.THEME_COLOR)

    try:
        app = EngineeringApp()
        app.mainloop()
    except Exception:
        # En cas de crash, on affiche la trace pour debug (mode dev)
        if config.DEBUG:
            traceback.print_exc()
        raise


if __name__ == "__main__":
    main()