import re
import threading
from tkinter import Event

import customtkinter as ctk
import polars as pl
from backend.helper import get_unique_msa_from_master
from backend.redfinscraper import RedfinApi
from CTkListbox import CTkListbox
from CTkMessagebox import CTkMessagebox
from CTkToolTip import CTkToolTip

from .datapage import DataPage
from .filterspage import FiltersPage


class SearchPage(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.datapage = None
        self.label_font = ctk.CTkFont("Roboto", 34)
        self.MATCHES_TO_DISPLAY = 20  # performance and practicality
        self.auto_complete_series = get_unique_msa_from_master()
        self.current_auto_complete_series = None
        self.prev_search_bar_len = 0
        self.filters_page = FiltersPage(self.master, self)
        self.create_widgets()

    def create_widgets(self) -> None:
        """Create widgets."""
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
            self,
            corner_radius=10,
            height=35,
            text="Add Filters",
            command=self.change_to_filters_page,
        )
        CTkToolTip(
            self.redfin_filters_button,
            delay=0.25,
            message="Select filters for your search.",
        )
        self.search_bar = ctk.CTkEntry(
            self, height=40, corner_radius=40, placeholder_text="Search for an MSA"
        )
        self.suggestion_list_box = CTkListbox(
            self,
            text_color=("gray10", "#DCE4EE"),  # type: ignore
            border_width=2,
            command=lambda x: self.update_entry_on_autocomplete_select(x),
        )
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_button = ctk.CTkButton(
            self.search_frame,
            text="Search",
            fg_color="transparent",
            height=35,
            corner_radius=10,
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            command=self.validate_entry_box_and_search,
        )
        self.cache_chb = ctk.CTkCheckBox(self.search_frame, text="Use cache")

        self.columnconfigure((0, 2), weight=1)
        self.columnconfigure(1, weight=4)
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=4)
        self.rowconfigure(2, weight=10)

        self.top_text.grid(column=0, row=0, columnspan=3)

        self.redfin_filters_button.grid(column=0, row=1, padx=(0, 40), sticky="e")

        self.search_bar.grid(column=1, row=1, sticky="ew")

        self.suggestion_list_box.grid(column=1, row=2, sticky="new", pady=(10, 0))

        self.search_frame.columnconfigure(0, weight=1)
        self.search_frame.rowconfigure((0, 1), weight=1)
        # pady is hacky but whatever
        self.search_frame.grid(column=2, row=1, padx=(40, 0), pady=(46, 0))
        self.search_button.grid(column=0, row=0, sticky="w")
        self.cache_chb.grid(column=0, row=1, pady=(20, 0), sticky="w")

        self.suggestion_list_box.grid_remove()
        self.search_bar.bind(
            "<KeyRelease>", command=lambda x: self.update_suggestions_listbox(x)
        )

    def update_suggestions_listbox(self, x: Event | None) -> None:
        """Update the suggestions box based on the contents of 'self.search_bar'.

        Args:
            x (Event | None): ignored
        """
        cur_text = re.escape(self.search_bar.get())
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
            try:
                self.current_auto_complete_series.head(
                    self.MATCHES_TO_DISPLAY
                ).map_elements(
                    lambda msa: self.suggestion_list_box.insert(
                        "end", msa, border_width=2, border_color="gray"
                    ),
                    return_dtype=pl.Utf8,
                )
            except KeyError:
                # always throws a key error, doesnt matter to us, just pollutes logs
                pass
        self.prev_search_bar_len = len(cur_text)

    def update_entry_on_autocomplete_select(self, x: Event) -> None:
        """Suggestions list box callback for when a button in the list box is selected."""
        self.search_bar.delete(0, ctk.END)
        self.search_bar.insert(0, x)
        self.update_suggestions_listbox(None)

    def validate_entry_box_and_search(self) -> None:
        """Validate `self.search_bar` contents and search if the contents are an MSA name."""
        cur_text = self.search_bar.get()
        if len(cur_text) == 0:
            cur_text = r"!^"
        if any(self.auto_complete_series.str.contains(rf"{cur_text}$")):
            self.data_page = DataPage(self.master)
            self.data_page.grid(row=0, column=0, sticky="news")
            self.go_to_data_page(cur_text)
            self.search_metros_threaded(cur_text)
        else:
            CTkMessagebox(
                self,
                title="Error",
                message="Inputted name is not in MSA name list!",
                icon="warning",
            )

    def go_to_data_page(self, msa_name: str) -> None:
        """Switch to data page.

        Args:
            msa_name (str): Metropolitan Statistical Area name
        """
        if self.data_page is not None:
            self.grid_remove()
            self.data_page.grid()
            self.data_page.set_msa_name(msa_name)

    def search_metros_threaded(self, msa_name: str) -> None:
        """Search the given Metropolitan Statistical Area name for housing attributes.

        Args:
            msa_name (str): Metropolitan Statistical Area name
        """
        redfin_searcher = RedfinApi()
        lock = threading.Lock()
        with lock:
            threading.Thread(
                target=redfin_searcher.get_house_attributes_from_metro,
                args=(
                    msa_name,
                    self.filters_page.get_values(),
                    bool(self.cache_chb.get()),
                ),
                daemon=True,
            ).start()

    def change_to_filters_page(self) -> None:
        """Change to filters page."""
        if self.filters_page is not None:
            self.filters_page.grid(row=0, column=0, sticky="news")
            self.grid_remove()
            self.filters_page.grid()
