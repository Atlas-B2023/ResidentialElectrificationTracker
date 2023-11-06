import customtkinter as ctk

from searchpage import SearchPage
# from filters import RedfinFiltersWindow
# from datapage import Datapage


ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MSA Heater Searcher")
        self.geometry("600x400")
        self.minsize(width=600, height=400)
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.search_page_frame = SearchPage(master=self)
        self.search_page_frame.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = App()
    app.mainloop()
