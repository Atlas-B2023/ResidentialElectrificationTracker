# import tkinter as tk
# from tkinter import ttk
import customtkinter as ctk
import datetime
from backend.redfinscraper import RedfinApi

# exercise:
# convert the app to use ctk


class FiltersPage(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, search_page: ctk.CTkFrame, **kwargs):
        # main setup
        super().__init__(master, **kwargs)
        self.root = master
        self.search_page = search_page
        self.cur_year = datetime.datetime.now().year
        self.sold_within_list = [
            "Last 1 week",
            "Last 1 month",
            "Last 3 months",
            "Last 6 months",
            "Last 1 year",
            "Last 2 years",
            "Last 3 years",
            "Last 5 years",
        ]
        self.create_widgets()
        self.set_default_values()

    def create_widgets(self):
        # frames
        self.content_frame = ctk.CTkFrame(self)
        self.for_sale_sold_frame = ctk.CTkFrame(
            self.content_frame, width=300, height=100, fg_color="transparent"
        )
        self.stories_frame = ctk.CTkFrame(self.content_frame)
        self.year_built_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.home_type_frame = ctk.CTkFrame(self.content_frame)
        self.square_feet_frame = ctk.CTkFrame(self.content_frame)
        self.status_frame = ctk.CTkFrame(self.content_frame)
        self.sold_within_frame = ctk.CTkFrame(self.content_frame)
        self.price_range_frame = ctk.CTkFrame(self.content_frame)
        self.reset_apply_frame = ctk.CTkFrame(self.content_frame)

        # make more grid
        self.columnconfigure((0, 2), weight=1)
        self.columnconfigure(1, weight=30)
        self.content_frame.columnconfigure((0), weight=1, uniform="a")  # uniform
        self.for_sale_sold_frame.columnconfigure((0, 1), weight=1)
        self.stories_frame.columnconfigure((0, 1), weight=1)
        self.year_built_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.home_type_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.square_feet_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.status_frame.columnconfigure((0, 1, 2), weight=1)
        self.sold_within_frame.columnconfigure((0, 1), weight=1)
        self.price_range_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.reset_apply_frame.columnconfigure((0, 1), weight=1)

        self.rowconfigure((0, 2), weight=1)
        self.rowconfigure(1, weight=30)
        self.content_frame.rowconfigure(
            (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), weight=1, uniform="a"
        )
        self.for_sale_sold_frame.rowconfigure(0, weight=1)
        self.stories_frame.rowconfigure(0, weight=1)
        self.year_built_frame.rowconfigure((0, 1), weight=1)
        self.home_type_frame.rowconfigure((0, 1, 2), weight=1)
        self.square_feet_frame.rowconfigure((0, 1), weight=1)
        self.status_frame.rowconfigure((0, 1), weight=1)
        self.sold_within_frame.rowconfigure(0, weight=1)
        self.price_range_frame.rowconfigure((0, 1), weight=1)
        self.reset_apply_frame.rowconfigure(0, weight=1)

        # placing the frames
        self.content_frame.grid(row=1, column=1)
        self.for_sale_sold_frame.grid(row=0, column=0, sticky="nsew")
        self.stories_frame.grid(row=1, column=0, sticky="nesw")
        self.year_built_frame.grid(row=2, column=0, sticky="nesw")
        self.home_type_frame.grid(row=3, column=0, rowspan=2, sticky="nesw")
        self.square_feet_frame.grid(row=5, column=0, sticky="nesw")
        self.status_frame.grid(row=6, column=0)
        self.sold_within_frame.grid(row=7, column=0, sticky="nesw")
        self.price_range_frame.grid(row=8, column=0, rowspan=2, sticky="nesw")
        self.reset_apply_frame.grid(row=10, column=0)

        # Create the labels
        self.for_sale_sold_label = ctk.CTkLabel(
            self.for_sale_sold_frame, text="For Sale/Sold"
        )
        self.stories_label = ctk.CTkLabel(self.stories_frame, text="Stories")
        self.year_built_label = ctk.CTkLabel(self.year_built_frame, text="Year Built")
        self.home_type_label = ctk.CTkLabel(self.home_type_frame, text="Home Type")
        self.sqft_label = ctk.CTkLabel(self.square_feet_frame, text="Square Feet")
        self.sale_status_label = ctk.CTkLabel(
            self.status_frame, text="Status"
        )  # shouldnt be here
        self.price_range_label = ctk.CTkLabel(
            self.price_range_frame, text="Price Range"
        )
        self.price_range_from_label = ctk.CTkLabel(self.price_range_frame, text="From")
        self.price_range_to_label = ctk.CTkLabel(self.price_range_frame, text="To")
        self.year_built_from_label = ctk.CTkLabel(self.year_built_frame, text="From")
        self.year_built_to_label = ctk.CTkLabel(self.year_built_frame, text="To")
        self.sold_within_label = ctk.CTkLabel(
            self.sold_within_frame, text="Sold Within"
        )
        self.sold_within_from_label = ctk.CTkLabel(self.square_feet_frame, text="From")
        self.sold_within_to_label = ctk.CTkLabel(self.square_feet_frame, text="To")

        # Create the Buttons
        self.for_sale_sold_om = ctk.CTkOptionMenu(
            master=self.for_sale_sold_frame,
            values=[value.value for value in RedfinApi.SoldStatus],
            command=lambda x: self.status_within_activate_deactivate(x),
        )

        self.stories_om = ctk.CTkOptionMenu(
            self.stories_frame, values=[story.value for story in RedfinApi.Stories]
        )
        self.year_list = [str(x) for x in range(2010, self.cur_year + 1)]
        list.reverse(self.year_list)
        self.year_built_min_om = ctk.CTkOptionMenu(
            self.year_built_frame,
            values=self.year_list,  # add validation
        )

        self.year_built_max_om = ctk.CTkOptionMenu(
            self.year_built_frame,
            values=self.year_list,  # add validation
        )

        self.house_type_house_switch = ctk.CTkSwitch(self.home_type_frame, text="House")

        self.house_type_townhouse_switch = ctk.CTkSwitch(
            self.home_type_frame, text="Townhouse"
        )
        self.house_type_condo_switch = ctk.CTkSwitch(self.home_type_frame, text="Condo")
        self.house_type_mul_fam_switch = ctk.CTkSwitch(
            self.home_type_frame, text="Multi-Family"
        )
        self.sqft_list = [sqft.value for sqft in RedfinApi.Sqft]
        list.reverse(self.sqft_list)
        self.sqft_min_om = ctk.CTkOptionMenu(
            self.square_feet_frame,
            values=self.sqft_list,
        )
        self.sqft_max_om = ctk.CTkOptionMenu(
            self.square_feet_frame,
            values=self.sqft_list,
        )
        self.status_coming_soon_chb = ctk.CTkCheckBox(
            self.status_frame, text="Coming soon"
        )
        self.status_active_chb = ctk.CTkCheckBox(self.status_frame, text="Active")
        self.status_pending_chb = ctk.CTkCheckBox(
            self.status_frame, text="Under contract/Pending"
        )  # missing one i think
        self.sold_within_om = ctk.CTkOptionMenu(
            self.sold_within_frame, values=self.sold_within_list
        )
        self.price_list = [price.value for price in RedfinApi.Price]
        list.reverse(self.price_list)
        self.price_range_min_om = ctk.CTkOptionMenu(
            self.price_range_frame,
            values=self.price_list,
        )  # add validation here too
        self.price_range_max_om = ctk.CTkOptionMenu(
            self.price_range_frame,
            values=self.price_list,
        )

        self.reset_filters_button = ctk.CTkButton(
            self.reset_apply_frame,
            text="Reset Filters",
            command=self.set_default_values,
        )
        self.apply_filters_button = ctk.CTkButton(
            self.reset_apply_frame,
            text="Apply Filters",
            command=self.change_to_search_page,
        )

        # Placing the widgets
        self.for_sale_sold_label.grid(row=0, column=0)
        self.stories_label.grid(row=0, column=0)
        self.year_built_label.grid(row=0, column=0)
        self.home_type_label.grid(row=0, column=0)
        self.sqft_label.grid(row=0, column=0)
        self.sale_status_label.grid(row=0, column=0)
        self.price_range_label.grid(row=0, column=0)
        self.year_built_from_label.grid(row=1, column=0)
        self.year_built_to_label.grid(row=1, column=2)
        self.price_range_from_label.grid(row=1, column=0)
        self.price_range_to_label.grid(row=1, column=2)
        self.sold_within_label.grid(row=0, column=0)
        self.sold_within_from_label.grid(row=1, column=0)
        self.sold_within_to_label.grid(row=1, column=2)

        self.for_sale_sold_om.grid(row=0, column=1)
        self.stories_om.grid(row=0, column=1)
        self.year_built_min_om.grid(row=1, column=1)
        self.year_built_max_om.grid(row=1, column=3)
        self.sqft_min_om.grid(row=1, column=1)
        self.sqft_max_om.grid(row=1, column=3)
        self.sold_within_om.grid(row=0, column=1)
        self.price_range_min_om.grid(row=1, column=1)
        self.price_range_max_om.grid(row=1, column=3)
        self.house_type_house_switch.grid(row=1, column=0)
        self.house_type_townhouse_switch.grid(row=1, column=1)
        self.house_type_condo_switch.grid(row=2, column=0)
        self.house_type_mul_fam_switch.grid(row=2, column=1)
        self.status_coming_soon_chb.grid(row=1, column=0)
        self.status_active_chb.grid(row=1, column=1)
        self.status_pending_chb.grid(row=1, column=2)
        self.reset_filters_button.grid(row=0, column=0, sticky="nesw")
        self.apply_filters_button.grid(row=0, column=1, sticky="nesw")

    def set_default_values(self):
        self.for_sale_sold_om.set(RedfinApi.SoldStatus.SOLD)
        self.stories_om.set(RedfinApi.Stories.ONE)
        self.year_built_min_om.set(str(self.cur_year - 1))
        self.year_built_max_om.set(str(self.cur_year - 1))
        self.sold_within_om.set(self.sold_within_list[-1])
        self.price_range_max_om.set("None")
        self.price_range_min_om.set("None")
        self.sqft_max_om.set("None")
        self.sqft_min_om.set("None")
        self.status_active_chb.deselect()
        self.status_pending_chb.deselect()
        self.status_coming_soon_chb.deselect()
        self.house_type_house_switch.select()
        self.house_type_condo_switch.deselect()
        self.house_type_townhouse_switch.deselect()
        self.house_type_mul_fam_switch.deselect()
        self.status_within_activate_deactivate(self.for_sale_sold_om.get())

    def status_within_activate_deactivate(self, status):
        """Deactivates or activates the status and sold within sections, since they depend on what type of sale a house is being searched with."""
        match self.for_sale_sold_om.get():
            case RedfinApi.SoldStatus.FOR_SALE.value:
                self.sale_status_label.configure(state="normal")
                self.status_active_chb.configure(state="normal")
                self.status_coming_soon_chb.configure(state="normal")
                self.status_pending_chb.configure(state="normal")
                self.sold_within_label.configure(state="disabled")
                self.sold_within_om.configure(state="disabled")
            case RedfinApi.SoldStatus.SOLD.value:
                # TODO make these filters compatible with tool
                self.sale_status_label.configure(state="disabled")
                self.status_active_chb.configure(state="disabled")
                self.status_coming_soon_chb.configure(state="disabled")
                self.status_pending_chb.configure(state="disabled")
                self.sold_within_label.configure(state="normal")
                self.sold_within_om.configure(state="normal")

    def change_to_search_page(self):
        self.grid_remove()
        self.search_page.grid()

    def get_values(self):
        self.for_sale_sold_om.get()
        self.stories_om.get()
        self.sqft_max_om.get()
        self.sqft_min_om.get()
        self.year_built_max_om.get()
        self.year_built_min_om.get()
        self.price_range_max_om.get()
        self.price_range_min_om.get()
        self.status_active_chb.get()
        self.status_coming_soon_chb.get()
        self.status_pending_chb.get()
        self.sold_within_om.get()
        self.house_type_house_switch.get()
        self.house_type_townhouse_switch.get()
        self.house_type_mul_fam_switch.get()
        self.house_type_condo_switch.get()
