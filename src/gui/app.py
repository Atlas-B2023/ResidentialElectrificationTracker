import customtkinter as ctk

from .searchpage import SearchPage
# from filters import RedfinFiltersWindow
# from datapage import Datapage


ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MSA Heater Searcher")
        # wxh
        self.desired_geometry_string = "800x600"
        self.geometry(self.desired_geometry_string)
        self.minsize(width=800, height=500)
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.searchpage_frame = SearchPage(master=self)
        self.searchpage_frame.grid(row=0, column=0, sticky="nsew")
