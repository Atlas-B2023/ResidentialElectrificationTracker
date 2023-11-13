import customtkinter as ctk
from CTkToolTip import CTkToolTip
from CTkListbox import CTkListbox
from CTkMessagebox import CTkMessagebox
from tkinter import Event
import polars as pl
import threading
from backend.RedfinSearcher import RedfinSearcher as rfs

# import os
# import sys

from backend.Helper import get_unique_msa_from_master
# from filters import RedfinFiltersWindow


class SearchPage(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs):
        super().__init__(master, **kwargs)
        self.datapage = None
        self.label_font = ctk.CTkFont("Roboto", 34)
        self.MATCHES_TO_DISPLAY = 20  # performance and practicality
        self.auto_complete_series = get_unique_msa_from_master()
        self.current_auto_complete_series = None
        self.prev_search_bar_len = 0
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
            master=self,
            text_color=("gray10", "#DCE4EE"),  # type: ignore
            border_width=2,
            command=lambda x: self.update_entry_on_autocomplete_select(x),
        )
        self.search_button = ctk.CTkButton(
            self,
            text="Search",
            fg_color="transparent",
            height=35,
            corner_radius=10,
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            command=self.validate_entry_box_and_search,
        )

        # make 2 rows, 3 cols
        self.columnconfigure((0, 2), weight=1)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(2, weight=10)

        # put widgets in grid
        self.top_text.grid(column=0, row=0, columnspan=3)

        self.redfin_filters_button.grid(column=0, row=1, padx=(0, 40), sticky="e")

        self.search_bar.grid(column=1, row=1, sticky="ew")

        self.suggestion_list_box.grid(column=1, row=2, sticky="new", pady=(10, 0))

        self.search_button.grid(column=2, row=1, padx=(40, 0), sticky="w")

        # misc
        self.suggestion_list_box.grid_remove()
        self.search_bar.bind(
            "<KeyRelease>", command=lambda x: self.update_suggestions_listbox(x)
        )
        # self.suggestion_list_box.bind("<ListboxSelection>", lambda x: self.update_entry_on_autocomplete_select(x))

    def update_suggestions_listbox(self, x: Event | None):
        cur_text = self.search_bar.get()
        if cur_text == "":
            # only gets called when all text has been deleted
            self.current_auto_complete_series = self.auto_complete_series
            self.suggestion_list_box.grid_remove()
        else:
            self.suggestion_list_box.delete("all")
            if (
                self.current_auto_complete_series is None
                or len(cur_text) < self.prev_search_bar_len
            ):
                self.current_auto_complete_series = self.auto_complete_series.filter(
                    self.auto_complete_series.str.contains(rf"(?i)^{cur_text}")
                )
            else:
                self.current_auto_complete_series = (
                    self.current_auto_complete_series.filter(
                        self.current_auto_complete_series.str.contains(
                            rf"(?i)^{cur_text}"
                        )
                    )
                )
            self.suggestion_list_box.grid()
            self.current_auto_complete_series.head(
                self.MATCHES_TO_DISPLAY
            ).map_elements(
                lambda msa: self.suggestion_list_box.insert(
                    "end", msa, border_width=2, border_color="gray"
                ),
                return_dtype=pl.Utf8,
            )
        self.prev_search_bar_len = len(cur_text)

    def update_entry_on_autocomplete_select(self, x: Event):
        self.search_bar.delete(0, ctk.END)
        self.search_bar.insert(0, x)
        self.update_suggestions_listbox(None)

    def validate_entry_box_and_search(self):
        cur_text = self.search_bar.get()
        if len(cur_text) == 0:
            cur_text = r"!^"
        if any(self.auto_complete_series.str.contains(rf"{cur_text}$")):
            self.search_metros_threaded(cur_text)
            self.go_to_data_page(cur_text)
        else:
            CTkMessagebox(
                self,
                title="Error",
                message="Inputted name is not in MSA name list!",
                icon="warning",
            )

    def go_to_data_page(self, msa_name: str):
        if self.datapage is not None:
            self.grid_remove()
            self.datapage.grid()
            self.datapage.set_msa_name(msa_name)

    def set_datapage(self, datapage):
        self.datapage = datapage

    def search_metros_threaded(self, metro_name: str):
        # get filters . submit button will validate them
        redfin_searcher = rfs(
            filters_path=rfs.generate_filters_path(
                sort=rfs.Sort.MOST_RECENTLY_SOLD,
                property_type=rfs.PropertyType.HOUSE,
                min_year_built=2022,
                max_year_built=2022,
                include=rfs.Include.LAST_5_YEAR,
                min_stories=rfs.Stories.ONE,
            )
        )
        lock = threading.Lock()
        with lock:
            my_thread = threading.Thread(
                target=redfin_searcher.load_house_attributes_from_metro_to_file,
                args=("TEST",),
                daemon=True,
            ).start()
