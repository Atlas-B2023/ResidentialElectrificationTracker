import customtkinter as ctk

from .searchpage import SearchPage

ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MSA Residential Heating Searcher")
        # wxh
        self.geometry("800x550")
        self.minsize(width=800, height=550)
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.search_page_frame = SearchPage(master=self)
        self.search_page_frame.grid(row=0, column=0, sticky="nsew")
