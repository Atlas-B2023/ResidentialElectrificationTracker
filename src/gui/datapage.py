import customtkinter as ctk
from datetime import datetime
from backend import Helper


class DataPage(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, **kwargs):
        super().__init__(master, **kwargs)
        self.searchpage = None
        self.msa_name = None
        self.create_widgets()

    def create_widgets(self):
        # copy paste for state metro and zip
        # width_by_3 = int(int(self.winfo_geometry().split("x")[0]) / 3)

        # three bars
        self.state_frame = ctk.CTkFrame(self, border_width=2)
        self.metro_frame = ctk.CTkFrame(self, border_width=2)
        self.zip_frame = ctk.CTkFrame(self, border_width=2)

        # display column name and dropdown filters
        self.state_banner_frame = ctk.CTkFrame(self.state_frame, border_width=2)
        self.metro_banner_frame = ctk.CTkFrame(self.metro_frame, border_width=2)
        self.zip_banner_frame = ctk.CTkFrame(self.zip_frame, border_width=2)

        self.state_banner_text = ctk.CTkLabel(
            self.state_banner_frame, text="State Statistics"
        )
        self.metro_banner_text = ctk.CTkLabel(
            self.metro_banner_frame, text="Metropolitan Statistics"
        )
        self.zip_banner_text = ctk.CTkLabel(
            self.zip_banner_frame, text="ZIP Code Statistics"
        )

        # nested frame for holding filters and text inside banner frame
        self.state_dropdown_frame = ctk.CTkFrame(self.state_banner_frame)
        self.metro_dropdown_frame = ctk.CTkFrame(self.metro_banner_frame)
        self.zip_dropdown_frame = ctk.CTkFrame(self.zip_banner_frame)

        cur_year = datetime.now().year
        years = [
            str(cur_year),
            str(cur_year - 1),
            str(cur_year - 2),
            str(cur_year - 3),
            str(cur_year - 4),
        ]
        # can make helper for get state in metros,
        self.state_select_state_dropdown_button = ctk.CTkOptionMenu(
            self.state_dropdown_frame,
            values=None,
        )
        self.state_select_year_dropdown_button = ctk.CTkOptionMenu(
            self.state_dropdown_frame, values=years
        )
        self.metro_select_year_dropdown_button = ctk.CTkOptionMenu(
            self.metro_dropdown_frame, values=years
        )
        self.zip_select_zip_dropdown_button = ctk.CTkOptionMenu(
            self.zip_dropdown_frame, values=None
        )
        self.zip_select_year_dropdown_button = ctk.CTkOptionMenu(
            self.zip_dropdown_frame, values=years
        )

        self.progress_bar_frame = ctk.CTkFrame(self, border_width=2)
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_bar_frame, orientation="horizontal"
        )
        # need some shared memory or queue to get current zip codes and completed zip codes https://pythonforthelab.com/blog/handling-and-sharing-data-between-threads/
        # can get total by getting list from helper func when creating the frame. and get completed by using `watchdog` to scan for dir changes in the metros folder
        self.progress_words = ctk.CTkLabel(
            self.progress_bar_frame, text="18/713 ZIP codes"
        )

        # grid
        # col
        self.columnconfigure((0, 1, 2), weight=1)

        self.state_frame.columnconfigure((0, 1), weight=1)
        self.metro_frame.columnconfigure((0, 1), weight=1)
        self.zip_frame.columnconfigure((0, 1), weight=1)

        self.state_banner_frame.columnconfigure((0, 1), weight=1)
        self.metro_banner_frame.columnconfigure((0, 1), weight=1)
        self.zip_banner_frame.columnconfigure((0, 1), weight=1)

        self.state_dropdown_frame.columnconfigure((0, 1), weight=1)
        self.metro_dropdown_frame.columnconfigure(0, weight=1)
        self.zip_dropdown_frame.columnconfigure((0, 1), weight=1)

        self.progress_bar_frame.columnconfigure(0, weight=50)
        self.progress_bar_frame.columnconfigure(1, weight=1)
        # row
        self.rowconfigure(0, weight=50)
        self.rowconfigure(1, weight=1)

        self.state_frame.rowconfigure(0, weight=1)
        self.state_frame.rowconfigure((1, 2, 3), weight=10)
        self.metro_frame.rowconfigure(0, weight=1)
        self.metro_frame.rowconfigure((1, 2), weight=10)
        self.zip_frame.rowconfigure(0, weight=1)
        self.zip_frame.rowconfigure((1, 2), weight=10)

        self.state_banner_frame.rowconfigure(0, weight=1)
        self.metro_banner_frame.rowconfigure(0, weight=1)
        self.zip_banner_frame.rowconfigure(0, weight=1)

        self.state_dropdown_frame.rowconfigure((0, 1), weight=1)
        self.metro_dropdown_frame.rowconfigure(0, weight=1)
        self.zip_dropdown_frame.rowconfigure((0, 1), weight=1)

        self.progress_bar_frame.rowconfigure(0, weight=1)

        # placement
        self.state_frame.grid(column=0, row=0, sticky="news")
        self.metro_frame.grid(column=1, row=0, sticky="news")
        self.zip_frame.grid(column=2, row=0, sticky="news")

        self.state_banner_frame.grid(column=0, row=0, columnspan=2, sticky="news")
        self.metro_banner_frame.grid(column=0, row=0, columnspan=2, sticky="news")
        self.zip_banner_frame.grid(column=0, row=0, columnspan=2, sticky="news")

        self.state_banner_text.grid(column=0, row=0, sticky="nsew")
        self.metro_banner_text.grid(column=0, row=0, sticky="nsew")
        self.zip_banner_text.grid(column=0, row=0, sticky="nsew")

        self.state_dropdown_frame.grid(column=1, row=0)
        self.metro_dropdown_frame.grid(column=1, row=0)
        self.zip_dropdown_frame.grid(column=1, row=0)

        self.state_select_year_dropdown_button.grid(column=1, row=1)
        self.state_select_state_dropdown_button.grid(column=0, row=1)
        self.metro_select_year_dropdown_button.grid(column=0, row=1)
        self.zip_select_zip_dropdown_button.grid(column=0, row=1)
        self.zip_select_year_dropdown_button.grid(column=1, row=1)

        self.progress_bar_frame.grid(row=1, column=0, columnspan=3, sticky="news")
        self.progress_bar.grid(column=0, row=0, sticky="we")
        self.progress_words.grid(column=1, row=0, sticky="e", padx=(0, 20))
        # btn = ctk.CTkButton(self, text="Press me", command=self.go_back_to_search_page)

    def go_back_to_search_page(self):
        if self.searchpage is not None:
            self.grid_remove()
            self.searchpage.grid()

    def set_searchpage(self, searchpage):
        self.searchpage = searchpage

    def set_msa_name(self, msa_name: str):
        self.msa_name = msa_name
        state_list = Helper.get_states_in_msa(self.msa_name)
        if len(state_list) > 0:
            self.state_select_state_dropdown_button.configure()
            self.state_select_state_dropdown_button.set(state_list[0])
        self.state_select_state_dropdown_button.configure(
            values=Helper.get_states_in_msa(self.msa_name)
        )

        zip_list = Helper.metro_name_to_zip_code_list(msa_name)
        zip_list = [str(zip) for zip in zip_list]
        self.zip_select_zip_dropdown_button.configure(values=zip_list)
        if len(zip_list) > 0:
            self.zip_select_zip_dropdown_button.set(zip_list[0])
