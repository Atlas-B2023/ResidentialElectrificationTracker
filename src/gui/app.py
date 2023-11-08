import customtkinter as ctk

from .searchpage import SearchPage
from .datapage import DataPage
# from filters import RedfinFiltersWindow
# from datapage import Datapage


ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MSA Heater Searcher")
        # wxh
        self.desired_geometry_string = "700x400"
        self.geometry(self.desired_geometry_string)
        self.minsize(width=600, height=400)
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.searchpage_frame = SearchPage(master=self)
        self.datapage_frame = DataPage(master=self)
        self.searchpage_frame.set_datapage(self.datapage_frame)
        self.datapage_frame.set_searchpage(self.searchpage_frame)
        self.datapage_frame.grid(row=0, column=0, sticky="nsew")
        self.searchpage_frame.grid(row=0, column=0, sticky="nsew")
        self.datapage_frame.grid_remove()
