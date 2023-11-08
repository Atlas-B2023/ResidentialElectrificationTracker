import customtkinter as ctk


class DataPage(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs):
        super().__init__(master, **kwargs)
        self.searchpage = None
        self._master = master
        self.create_widgets()

    def create_widgets(self):
        btn = ctk.CTkButton(self, text="Press me", command=self.go_back_to_search_page)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        btn.grid(column=0, row=0)

    def go_back_to_search_page(self):
        if self.searchpage is not None:
            self.grid_remove()
            self.searchpage.grid()

    def set_searchpage(self, searchpage):
        self.searchpage = searchpage
