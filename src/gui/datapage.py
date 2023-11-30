import threading
import webbrowser
import datetime
from matplotlib import pyplot as plt
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import sys
import subprocess


# from matplotlib.backend_bases import key_press_handler
from backend import helper, EIADataRetriever
from backend.us import states as sts
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.figure import Figure
from backend.helper import log
from backend.secondarydata import CensusDataRetriever

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
        self.cur_year = datetime.datetime.now().year
        self.years = [
            str(self.cur_year),
            str(self.cur_year - 1),
            str(self.cur_year - 2),
            str(self.cur_year - 3),
            str(self.cur_year - 4),
        ]
        self.roboto_font = ctk.CTkFont(family="Roboto")
        self.roboto_header_font = ctk.CTkFont(family="Roboto", size=28)
        self.roboto_link_font = ctk.CTkFont(family="Roboto", underline=True, size=20)
        self.create_widgets()

    def create_widgets(self) -> None:
        """Create widgets."""
        # bug in sockets library wont allow you to raise keyboardinterrupt, so stopping
        # Content frame will have 4 rows. first will be header, 2nd is energy graph, 3rd will contain a frame that has censusreport.org links, 4th will have progress bar frame
        self.content_frame = ctk.CTkFrame(self, border_width=2)
        self.content_banner_frame = ctk.CTkFrame(self.content_frame, border_width=2)
        self.state_and_year_content_banner_dropdown_frame = ctk.CTkFrame(
            self.content_banner_frame, border_width=2
        )
        self.census_reporter_frame = ctk.CTkFrame(self.content_frame, border_width=2)
        self.log_frame = ctk.CTkFrame(self.content_frame, border_width=2)

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
            values=self.years,
            command=self.year_dropdown_callback,
        )

        self.energy_graph_frame = ctk.CTkFrame(self.content_frame, border_width=2)

        self.census_reporter_state_label = ctk.CTkLabel(
            self.census_reporter_frame,
            text="Census Reporter: State Report",
            font=self.roboto_link_font,
            cursor="hand2",
            text_color="blue",
        )

        self.log_button = ctk.CTkButton(
            self.log_frame, text="Open Log File", command=self.open_log_file
        )
        self.census_button = ctk.CTkButton(
            self.log_frame,
            text="Generate Census data",
            command=self.generate_census_reports,
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
        self.log_frame.columnconfigure((0, 1), weight=1)

        # row
        self.rowconfigure(0, weight=1)

        self.content_frame.rowconfigure(0, weight=1)  # banner
        self.content_frame.rowconfigure(1, weight=5)  # energy graph
        self.content_frame.rowconfigure(2, weight=2)  # census reporter frame
        self.content_frame.rowconfigure(3, weight=1)

        self.content_banner_frame.rowconfigure(0, weight=1)

        self.state_and_year_content_banner_dropdown_frame.rowconfigure((0, 1), weight=1)

        self.energy_graph_frame.rowconfigure(0, weight=1)

        self.census_reporter_frame.rowconfigure((0, 1), weight=1)

        self.log_frame.rowconfigure(0, weight=1)

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

        self.log_frame.grid(column=0, row=3, sticky="news")
        self.census_button.grid(column=0, row=0, pady=10, padx=(0, 10))
        self.log_button.grid(column=1, row=0, pady=10, padx=(10, 0))

    def set_msa_name(self, msa_name: str) -> None:
        """Set the msa name and update objects that rely on the msa name. Includes drop downs and and generating the energy plot.

        Args:
            msa_name (str): Metropolitan Statistical Area name. This must be validated
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

    def generate_energy_plot(self, year: int, state: str) -> None:
        """Call the EIA API and generate a plot with the received data.

        Note:
            Call this in a thread so that it doesn't freeze the GUI
            Update: might want to just get the data and plot on the main thread
        """
        eia = EIADataRetriever()
        energy_price_per_mbtu_by_type_for_state = (
            eia.monthly_price_per_mbtu_by_energy_type_by_state(
                state, datetime.date(year, 1, 1), datetime.date(year + 1, 1, 1)
            )
        )

        fig = Figure(layout="compressed", facecolor="#dbdbdb")
        ax = fig.add_subplot()
        ax.set_xlabel("Time (Months)")
        ax.set_ylabel("Cost per Effective MBTU ($/MBTU)")
        ax.set_title(
            f"Avg. Energy Prices by Appliance for {state}, {year}",
            loc="center",
            wrap=True,
        )
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

        for energy_dict in energy_price_per_mbtu_by_type_for_state:
            if len(energy_dict) < 3:
                log(
                    f"Issue with energy type {energy_dict.get("type")} for state {energy_dict.get("state")}",
                    "debug",
                )
                continue
            match energy_dict.get("type"):
                case EIADataRetriever.EnergyType.PROPANE.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Propane Furnace")
                case EIADataRetriever.EnergyType.HEATING_OIL.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Heating Oil Boiler")
                case EIADataRetriever.EnergyType.NATURAL_GAS.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Natural Gas Furnace")
                case EIADataRetriever.EnergyType.ELECTRICITY.value:
                    result_list = []
                    for month in months:
                        key = f"{year}-{month:02}"
                        val = energy_dict.get(key, float("NaN"))
                        if val is None:
                            val = float("NaN")
                        result_list.append(val)
                    ax.plot(months, result_list, label="Ducted Heat Pump")
        ax.legend()
        with threading.Lock():
            canvas = FigureCanvasTkAgg(fig, master=self.energy_graph_frame)
            canvas.draw()

            # toolbar = NavigationToolbar2Tk(canvas, window=self.energy_graph_frame, pack_toolbar=False)
            # toolbar.update()
            # canvas.mpl_connect("key_press_event", key_press_handler)

            # toolbar.grid(column=0, row=1, sticky="news")
            canvas.get_tk_widget().grid(column=0, row=0)

    def open_census_reporter_state(self) -> None:
        """Census reporter state label callback"""
        state_link = helper.get_census_report_url_page(
            sts.lookup(self.select_state_dropdown.get()).name  # type: ignore
        )
        webbrowser.open_new_tab(state_link)

    def open_census_reporter_metro(self) -> None:
        """Census reporter metro label callback"""
        metro_link = helper.get_census_report_url_page(f"{self.msa_name} metro area")  # type: ignore
        webbrowser.open_new_tab(metro_link)

    def state_dropdown_callback(self, state: str) -> None:
        """Banner state callback.
        TODO:
            check if thread is running with given name, and if so join it and start the new thread

        Args:
            state (str): the state after the change
        """

        threading.Thread(
            target=self.generate_energy_plot,
            args=(
                int(self.select_year_dropdown.get()),
                state,
            ),
            name="energy_thread",
            daemon=True,
        ).start()

    def year_dropdown_callback(self, year: str) -> None:
        """Banner year callback.
        TODO:
            Check if thread is running with given name, and if so join it and start the new thread

        Args:
            year (str): the year after the change
        """
        threading.Thread(
            target=self.generate_energy_plot,
            args=(
                int(year),
                self.select_state_dropdown.get(),
            ),
            name="energy_thread",
            daemon=True,
        ).start()

    def open_log_file(self) -> None:
        """Open logging file.

        Note:
            Haven't tested this on mac/linux. "darwin" doesn't exist in `system.platform` on windows, so cant say for sure if this works
        """
        try:
            if sys.platform == "win32":
                from os import startfile

                startfile(helper.LOGGING_FILE_PATH)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.call([opener, helper.LOGGING_FILE_PATH])
        except FileNotFoundError:
            CTkMessagebox(
                self,
                title="Error",
                message="Logging file doesn't exist! Try rerunning the program or creating a logger.log file in /output/logging/",
                icon="warning",
            )

    def generate_census_reports(self) -> None:
        log("Fetching census reports...", "info")
        c = CensusDataRetriever()
        threading.Thread(
            target=c.generate_acs5_subject_table_group_for_zcta_by_year,
            args=(
                "S1901",
                "2019",
            ),
        ).start()
        threading.Thread(
            target=c.generate_acs5_profile_table_group_for_zcta_by_year,
            args=(
                "DP05",
                "2019",
            ),
        ).start()
