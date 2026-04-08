from pathlib import Path

import customtkinter as ctk

import ui.theme as theme


def main():
    """Entry point: load branding, configure CTk, launch the app."""
    theme.load(Path(__file__).parent / "branding.json")
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    from ui.app import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
