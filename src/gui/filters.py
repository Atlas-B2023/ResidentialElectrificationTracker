from typing import Tuple
import customtkinter as ctk


class RedfinFiltersWindow(ctk.CTkToplevel):
    def __init__(self, *args, fg_color: str | Tuple[str, str] | None = None, **kwargs):
        super().__init__(*args, fg_color=fg_color, **kwargs)
        self.title("Redfin Filters")
        self.geometry("400x600")
        self.create_widgets()

    def create_widgets(self):
        pass

    def launch(self):
        pass
