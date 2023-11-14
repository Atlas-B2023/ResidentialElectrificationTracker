import customtkinter as ctk
import webbrowser
from datetime import datetime
from backend import Helper
from backend.us import states as sts

# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from matplotlib.figure import Figure
from matplotlib import pyplot as plt

plt.style.use("fivethirtyeight")


class DataPage(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.msa_name = None
        self.income_df = None
        self.demog_df = None
        self.states_in_msa = None
        self.state_demog_dfs = None
        self.state_income_dfs = None
        self.roboto_font = ctk.CTkFont(family="Roboto")
        self.roboto_header_font = ctk.CTkFont(family="Roboto", size=20)
        self.roboto_link_font = ctk.CTkFont(family="Roboto", underline=True)
        self.create_widgets()
        # threading.Thread(target=self.update_state_income_figure).start()

    def create_widgets(self):
        # copy paste for state metro and zip
        # width_by_3 = int(int(self.winfo_geometry().split("x")[0]) / 3)

        # Content frame will have 4 rows. first will be header, 2nd is energy graph, 3rd will contain a frame that has censusreport.org links, 4th will have progress bar frame
        self.content_frame = ctk.CTkFrame(self, border_width=2)
        self.content_banner_frame = ctk.CTkFrame(self.content_frame, border_width=2)
        self.state_and_year_content_banner_dropdown_frame = ctk.CTkFrame(
            self.content_banner_frame, border_width=2
        )
        self.census_reporter_frame = ctk.CTkFrame(self.content_frame, border_width=2)
        self.progress_bar_frame = ctk.CTkFrame(self.content_frame, border_width=2)

        self.content_banner_main_text = ctk.CTkLabel(
            self.content_banner_frame,
            text="Census and Energy Data:",
            font=self.roboto_header_font,
        )

        # nested frame for holding filters and text inside banner frame
        cur_year = datetime.now().year
        years = [
            str(cur_year),
            str(cur_year - 1),
            str(cur_year - 2),
            str(cur_year - 3),
            str(cur_year - 4),
        ]

        self.select_state_label = ctk.CTkLabel(
            self.state_and_year_content_banner_dropdown_frame,
            text="Select State",
            font=self.roboto_font,
        )
        self.select_state_dropdown = ctk.CTkOptionMenu(
            self.state_and_year_content_banner_dropdown_frame,
            values=None,
        )
        self.select_year_label = ctk.CTkLabel(
            self.state_and_year_content_banner_dropdown_frame,
            text="Select Year",
            font=self.roboto_font,
        )
        self.select_year_dropdown = ctk.CTkOptionMenu(
            self.state_and_year_content_banner_dropdown_frame, values=years
        )

        self.energy_graph_frame = ctk.CTkFrame(self.content_frame, border_width=2)

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_bar_frame, orientation="horizontal"
        )
        # need some shared memory or queue to get current zip codes and completed zip codes https://pythonforthelab.com/blog/handling-and-sharing-data-between-threads/
        # can get total by getting list from helper func when creating the frame. and get completed by using `watchdog` to scan for dir changes in the metros folder
        self.progress_words = ctk.CTkLabel(
            self.progress_bar_frame, text="18/713 ZIP codes", font=self.roboto_font
        )

        self.stop_search_button = ctk.CTkButton(
            self.progress_bar_frame, text="Stop search"
        )

        self.census_reporter_state_label = ctk.CTkLabel(
            self.census_reporter_frame,
            text="Census Reporter: State Report",
            font=self.roboto_link_font,
            cursor="hand2",
            text_color="blue",
        )
        self.census_reporter_state_label.bind("<Button-1>", lambda x: self.open_census_reporter_state())
        self.census_reporter_metro_label = ctk.CTkLabel(
            self.census_reporter_frame,
            text="Census Reporter: Metro Report",
            font=self.roboto_link_font,
            cursor="hand2",
            text_color="blue",
        )
        self.census_reporter_metro_label.bind("<Button-1>", lambda x: self.open_census_reporter_metro())
        # create grid
        # col
        self.columnconfigure(0, weight=1)

        self.content_frame.columnconfigure(0, weight=1)

        self.content_banner_frame.columnconfigure((0, 1), weight=1)
        self.state_and_year_content_banner_dropdown_frame.columnconfigure(
            (0, 1), weight=1
        )

        self.energy_graph_frame.columnconfigure(0, weight=1)

        self.census_reporter_frame.columnconfigure(0, weight=1)

        self.progress_bar_frame.columnconfigure(0, weight=50)  # bar
        self.progress_bar_frame.columnconfigure((1, 2), weight=1)  # text, button

        # row
        self.rowconfigure(0, weight=1)

        self.content_frame.rowconfigure(0, weight=1)  # banner
        self.content_frame.rowconfigure(1, weight=5)  # energy graph
        self.content_frame.rowconfigure(2, weight=2)  # census reporter frame
        self.content_frame.rowconfigure(3, weight=1)  # progress bar

        self.content_banner_frame.rowconfigure(0, weight=1)
        self.state_and_year_content_banner_dropdown_frame.rowconfigure((0, 1), weight=1)

        self.energy_graph_frame.rowconfigure(0, weight=1)

        self.census_reporter_frame.rowconfigure(
            (0, 1), weight=1
        )  # going to have two labels

        self.progress_bar_frame.rowconfigure(0, weight=1)

        # placement
        self.content_frame.grid(column=0, row=0, sticky="news")

        self.content_banner_frame.grid(column=0, row=0, sticky="news")

        self.content_banner_main_text.grid(column=0, row=0, sticky="nsew")

        self.state_and_year_content_banner_dropdown_frame.grid(
            column=1, row=0, sticky="news"
        )

        self.select_state_label.grid(column=0, row=0, sticky="news")
        self.select_year_label.grid(column=1, row=0, sticky="news")
        self.select_state_dropdown.grid(column=0, row=1)
        self.select_year_dropdown.grid(column=1, row=1)

        self.energy_graph_frame.grid(column=0, row=1, sticky="news")

        self.census_reporter_frame.grid(column=0, row=2, sticky="news")
        self.census_reporter_state_label.grid(column=0, row=0)
        self.census_reporter_metro_label.grid(column=0, row=1)
        self.progress_bar_frame.grid(column=0, row=3, sticky="news")
        self.progress_bar.grid(column=0, row=0, sticky="we")
        self.progress_words.grid(column=1, row=0, sticky="e", padx=(0, 20))
        self.stop_search_button.grid(column=2, row=0, sticky="w")

    def set_msa_name(self, msa_name: str):
        self.msa_name = msa_name
        self.states_in_msa = Helper.get_states_in_msa(self.msa_name)

        if len(self.states_in_msa) > 0:
            self.select_state_dropdown.configure()
            self.select_state_dropdown.set(self.states_in_msa[0])

        self.select_state_dropdown.configure(values=self.states_in_msa)
        self.content_banner_main_text.configure(
            text=f"Census and Energy Data: {self.msa_name}"
        )
        self.zip_list = Helper.metro_name_to_zip_code_list(msa_name)
        self.zip_list = [str(zip) for zip in self.zip_list]

    def open_census_reporter_state(self):
        state_link = Helper.get_census_report_url_page(
            sts.lookup(self.select_state_dropdown.get()).name  # type: ignore
        )
        webbrowser.open_new_tab(state_link)

    def open_census_reporter_metro(self):
        metro_link = Helper.get_census_report_url_page(f"{self.msa_name} metro area") # type: ignore
        webbrowser.open_new_tab(metro_link)
