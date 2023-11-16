import threading
import webbrowser
import datetime

from matplotlib import pyplot as plt
import customtkinter as ctk
from backend import helper, EIADataRetriever
from backend.us import states as sts
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

plt.style.use("fivethirtyeight")


class DataPage(ctk.CTkFrame):
    """Crate page for displaying energy data and links to censusreporter.org for census level data"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.msa_name = None
        self.income_df = None
        self.demog_df = None
        self.states_in_msa = None
        self.state_demog_dfs = None
        self.state_income_dfs = None
        self.roboto_font = ctk.CTkFont(family="Roboto")
        self.roboto_header_font = ctk.CTkFont(family="Roboto", size=28)
        self.roboto_link_font = ctk.CTkFont(family="Roboto", underline=True, size=20)
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
        self.content_banner_main_text.bind(
            "<Configure>",
            command=lambda x: self.content_banner_main_text.configure(
                wraplength=self.content_banner_main_text._current_width
                - 40  # random padding
            ),
        )
        # nested frame for holding filters and text inside banner frame
        cur_year = datetime.datetime.now().year
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
            command=self.state_dropdown_callback,
        )

        self.select_year_label = ctk.CTkLabel(
            self.state_and_year_content_banner_dropdown_frame,
            text="Select Year",
            font=self.roboto_font,
        )
        self.select_year_dropdown = ctk.CTkOptionMenu(
            self.state_and_year_content_banner_dropdown_frame,
            values=years,
            command=self.year_dropdown_callback,
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
        self.census_reporter_state_label.bind(
            "<Button-1>", lambda x: self.open_census_reporter_state()
        )
        self.census_reporter_metro_label = ctk.CTkLabel(
            self.census_reporter_frame,
            text="Census Reporter: Metro Report",
            font=self.roboto_link_font,
            cursor="hand2",
            text_color="blue",
        )
        self.census_reporter_metro_label.bind(
            "<Button-1>", lambda x: self.open_census_reporter_metro()
        )
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
        self.progress_bar.grid(column=0, row=0, sticky="we", padx=(20, 0))
        self.progress_words.grid(column=1, row=0, sticky="e", padx=(0, 20))
        self.stop_search_button.grid(column=2, row=0, sticky="w")

    def set_msa_name(self, msa_name: str):
        """set the msa name

        Args:
            msa_name (str): msa name. This must be validated
        """
        self.msa_name = msa_name
        self.states_in_msa = helper.get_states_in_msa(self.msa_name)

        if len(self.states_in_msa) > 0:
            self.select_state_dropdown.configure()
            self.select_state_dropdown.set(self.states_in_msa[0])

        self.select_state_dropdown.configure(values=self.states_in_msa)
        self.content_banner_main_text.configure(
            text=f"Census and Energy Data: {self.msa_name}"
        )
        self.zip_list = helper.metro_name_to_zip_code_list(msa_name)
        self.zip_list = [str(zip) for zip in self.zip_list]

        threading.Thread(
            target=self.generate_energy_plot,
            args=(
                int(self.select_year_dropdown.get()),
                self.select_state_dropdown.get(),
            ),
            daemon=True,
        ).start()

    def generate_energy_plot(self, year, state):
        """Calls the EIA API and generates a plot with the received data.

        Notes:
            Call this in a thread so that it doesn't freeze the GUI
        """
        eia = EIADataRetriever()
        energy_price_per_mbtu_by_type_for_state = (
            eia.monthly_price_per_million_btu_by_energy_type_by_state(
                state, datetime.date(year, 1, 1), datetime.date(year + 1, 1, 1)
            )
        )

        fig = Figure(layout="compressed", facecolor="blue")
        ax = fig.add_subplot()
        ax.set_xlabel("Time (Months)")
        ax.set_ylabel("Effective Cost ($/MBTU)")
        ax.set_title(f"Avg. Energy prices for {state}, {year}")
        months = [i for i in range(1, 13)]
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        ax.set_xticks(months)
        labels = [item.get_text() for item in ax.get_xticklabels()]

        # Modify specific labels, keeping offset
        for i in range(0, 12):
            labels[i] = month_names[i]
        ax.set_xticklabels(labels)
        # some months may not be present, some months may be present with None. must go to NaN
        # TODO investigate DC issues with api
        for energy_dict in energy_price_per_mbtu_by_type_for_state:
            print(f"Cur {energy_dict =}")
            match energy_dict.get("type"):
                case EIADataRetriever.EnergyTypes.PROPANE.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Propane")
                case EIADataRetriever.EnergyTypes.HEATING_OIL.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Heating Oil")
                case EIADataRetriever.EnergyTypes.NATURAL_GAS.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Natural Gas")
                case EIADataRetriever.EnergyTypes.ELECTRICITY.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Electricity")
        ax.legend()
        with threading.Lock():
            chart1 = FigureCanvasTkAgg(fig, self.energy_graph_frame)
            chart1.get_tk_widget().grid(column=0, row=0)

    def open_census_reporter_state(self):
        state_link = helper.get_census_report_url_page(
            sts.lookup(self.select_state_dropdown.get()).name  # type: ignore
        )
        webbrowser.open_new_tab(state_link)

    def open_census_reporter_metro(self):
        metro_link = helper.get_census_report_url_page(f"{self.msa_name} metro area")  # type: ignore
        webbrowser.open_new_tab(metro_link)

    def state_dropdown_callback(self, state):
        # update energy chart, choice is 2 char postal code

        threading.Thread(
            target=self.generate_energy_plot,
            args=(
                int(self.select_year_dropdown.get()),
                state,
            ),
            daemon=True,
        ).start()

    def year_dropdown_callback(self, year):
        # update energy chart, choice is year
        threading.Thread(
            target=self.generate_energy_plot,
            args=(
                int(year),
                self.select_state_dropdown.get(),
            ),
            daemon=True,
        ).start()
