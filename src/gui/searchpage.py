import customtkinter as ctk
# from filters import RedfinFiltersWindow


class SearchPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.create_widgets()
        # self.redfin_filters = RedfinFiltersWindow(takefocus=True)

    def create_widgets(self):
        # https://www.tutorialspoint.com/how-to-create-hyperlink-in-a-tkinter-text-widget for hyper link
        top_text = ctk.CTkLabel(
            self, text="Residential Heating Search For Metropolitan Statistical Areas"
        )
        redfin_filters_button = ctk.CTkButton(
            self, text="Add Filters"
        )  # , command=redfin_filters.launch
        search_bar = ctk.CTkEntry(self, placeholder_text="Search for an MSA")
        search_button = ctk.CTkButton(
            self,
            text="Search",
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )

        # make 2 rows, 3 cols
        self.columnconfigure((0, 2), weight=1)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=8)

        # put widgets in grid
        top_text.grid(column=0, row=0, columnspan=3)
        redfin_filters_button.grid(column=0, row=1)
        redfin_filters_button.grid_anchor("ne")
        search_bar.grid(column=1, row=1, sticky="ew")
        search_bar.grid_anchor("n")
        search_button.grid(column=2, row=1)
        search_button.grid_anchor("nw")
