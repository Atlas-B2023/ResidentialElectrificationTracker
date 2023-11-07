import customtkinter as ctk
from CTkToolTip import CTkToolTip
from CTkListbox import CTkListbox
import re
# from filters import RedfinFiltersWindow


class SearchPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.label_font = ctk.CTkFont("Roboto", 34)
        self.entry_str_var = ctk.StringVar()
        self.auto_complete_list = [
            "hi",
            "there",
            "obiwan",
            "new yourk",
            "new York",
            "new jersy",
            "new jersey",
        ]
        self.create_widgets()

        # self.redfin_filters = RedfinFiltersWindow(takefocus=True)

    def create_widgets(self):
        # https://www.tutorialspoint.com/how-to-create-hyperlink-in-a-tkinter-text-widget for hyper link
        self.top_text = ctk.CTkLabel(
            self,
            text="Residential Heating Search For Metropolitan Statistical Areas",
            font=self.label_font,
            wraplength=600,
        )
        CTkToolTip(
            self.top_text,
            delay=0.25,
            message="An MSA is a census defined region that consists of a city and \nsurrounding communities that are linked by social and economic factors. \nThe core city has a population of at least 50,000",
        )
        self.redfin_filters_button = ctk.CTkButton(
            self, corner_radius=10, height=35, text="Add Filters"
        )  # , command=redfin_filters.launch
        self.search_bar = ctk.CTkEntry(
            self, height=40, corner_radius=40, placeholder_text="Search for an MSA"
        )
        self.suggestion_list_box = CTkListbox(
            master=self, text_color=("gray10", "#DCE4EE"), border_width=2
        )
        self.search_button = ctk.CTkButton(
            self,
            text="Search",
            fg_color="transparent",
            height=35,
            corner_radius=10,
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )

        # make 2 rows, 3 cols
        self.columnconfigure((0, 2), weight=1)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=10)

        # put widgets in grid
        self.top_text.grid(column=0, row=0, columnspan=3)

        self.redfin_filters_button.grid(column=0, row=1, padx=(0, 40), sticky="e")

        self.search_bar.grid(column=1, row=1, sticky="ew")

        self.suggestion_list_box.grid(column=1, row=2, sticky="new")

        self.search_button.grid(column=2, row=1, padx=(40, 0), sticky="w")

        # misc
        self.suggestion_list_box.grid_remove()
        self.search_bar.bind(
            "<KeyRelease>", command=lambda x: self.update_suggestions_listbox(x)
        )

    def update_suggestions_listbox(self, x):
        cur_text = self.search_bar.get()
        if cur_text == "":
            self.suggestion_list_box.grid_remove()
        else:
            self.suggestion_list_box.delete("all")
            matches = [
                re.search(rf"\b{cur_text}", msa, re.I)
                for msa in self.auto_complete_list
            ]
            self.suggestion_list_box.grid()
            print(matches)
            for match in matches:
                if match is not None:
                    self.suggestion_list_box.insert(
                        "end",
                        match.string,
                        border_width=2,
                        border_color="gray",
                    )
