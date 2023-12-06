import datetime
from typing import Any

import customtkinter as ctk
from backend.redfinscraper import RedfinApi


class FiltersPage(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, search_page: ctk.CTkFrame, **kwargs):
        # main setup
        super().__init__(master, **kwargs)
        self.root = master
        self.search_page = search_page
        self.cur_year = datetime.datetime.now().year
        self.year_list = [str(x) for x in range(2010, self.cur_year + 1)]
        list.reverse(self.year_list)
        self.sqft_list = [sqft.value for sqft in RedfinApi.Sqft]
        list.reverse(self.sqft_list)
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
        self.price_list = [price.value for price in RedfinApi.Price]
        list.reverse(self.price_list)
        self.create_widgets()
        self.set_default_values()

    def create_widgets(self) -> None:
        """Create widgets."""
        # frames
        self.content_frame = ctk.CTkFrame(self)
        self.for_sale_sold_frame = ctk.CTkFrame(
            self.content_frame, width=300, height=100, fg_color="transparent"
        )
        self.stories_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.year_built_frame = ctk.CTkFrame(
            self.content_frame, corner_radius=0, fg_color="transparent"
        )
        self.home_type_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.square_feet_frame = ctk.CTkFrame(
            self.content_frame, corner_radius=0, fg_color="transparent"
        )
        self.status_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.sold_within_frame = ctk.CTkFrame(
            self.content_frame, fg_color="transparent", corner_radius=0
        )
        self.price_range_frame = ctk.CTkFrame(self.content_frame, corner_radius=0)
        self.reset_apply_frame = ctk.CTkFrame(
            self.content_frame, fg_color="transparent", corner_radius=0
        )

        # make more grid
        self.columnconfigure((0, 2), weight=1)
        self.columnconfigure(1, weight=30)
        self.content_frame.columnconfigure(0, weight=1, uniform="a")  # uniform
        self.for_sale_sold_frame.columnconfigure((0, 1), weight=1)
        self.stories_frame.columnconfigure((0, 1), weight=1)
        self.year_built_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.home_type_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.square_feet_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.status_frame.columnconfigure((0, 1, 2), weight=1)
        self.sold_within_frame.columnconfigure((0, 1), weight=1)
        self.price_range_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.reset_apply_frame.columnconfigure((0, 1), weight=1)

        self.rowconfigure(0, weight=1)
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
        self.content_frame.grid(row=0, column=1, sticky="ns")
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
        self.sale_status_label = ctk.CTkLabel(self.status_frame, text="Status")
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
            values=[status.value for status in RedfinApi.SoldStatus],
            command=lambda x: self.status_within_activate_deactivate(x),
        )

        self.min_stories_om = ctk.CTkOptionMenu(
            self.stories_frame, values=[story.value for story in RedfinApi.Stories]
        )

        self.min_year_built_om = ctk.CTkOptionMenu(
            self.year_built_frame,
            values=self.year_list,
            command=lambda x: self.year_validation(),
        )

        self.max_year_built_om = ctk.CTkOptionMenu(
            self.year_built_frame,
            values=self.year_list,
            command=lambda x: self.year_validation(),
        )

        self.house_type_house_switch = ctk.CTkSwitch(
            self.home_type_frame,
            text="House",
            command=self.house_type_validation,
        )
        self.house_type_townhouse_switch = ctk.CTkSwitch(
            self.home_type_frame,
            text="Townhouse",
            command=self.house_type_validation,
        )
        self.house_type_condo_switch = ctk.CTkSwitch(
            self.home_type_frame,
            text="Condo",
            command=self.house_type_validation,
        )
        self.house_type_mul_fam_switch = ctk.CTkSwitch(
            self.home_type_frame,
            text="Multi-Family",
            command=self.house_type_validation,
        )

        self.min_sqft_om = ctk.CTkOptionMenu(
            self.square_feet_frame,
            values=self.sqft_list,
            command=lambda x: self.sqft_validation(),
        )
        self.max_sqft_om = ctk.CTkOptionMenu(
            self.square_feet_frame,
            values=self.sqft_list,
            command=lambda x: self.sqft_validation(),
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

        self.min_price_om = ctk.CTkOptionMenu(
            self.price_range_frame,
            values=self.price_list,
            command=lambda x: self.price_validation(),
        )
        self.max_price_om = ctk.CTkOptionMenu(
            self.price_range_frame,
            values=self.price_list,
            command=lambda x: self.price_validation(),
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
        self.min_stories_om.grid(row=0, column=1)
        self.min_year_built_om.grid(row=1, column=1)
        self.max_year_built_om.grid(row=1, column=3)
        self.min_sqft_om.grid(row=1, column=1)
        self.max_sqft_om.grid(row=1, column=3)
        self.sold_within_om.grid(row=0, column=1)
        self.min_price_om.grid(row=1, column=1)
        self.max_price_om.grid(row=1, column=3)
        self.house_type_house_switch.grid(row=1, column=0)
        self.house_type_townhouse_switch.grid(row=1, column=1)
        self.house_type_condo_switch.grid(row=2, column=0)
        self.house_type_mul_fam_switch.grid(row=2, column=1)
        self.status_coming_soon_chb.grid(row=1, column=0)
        self.status_active_chb.grid(row=1, column=1)
        self.status_pending_chb.grid(row=1, column=2)
        self.reset_filters_button.grid(row=0, column=0, sticky="w")
        self.apply_filters_button.grid(row=0, column=1, sticky="e")

    def set_default_values(self) -> None:
        """Set the default values for all widgets.
        Note:
            Should be called after init and when clicking reset button.
        """
        self.for_sale_sold_om.set(RedfinApi.SoldStatus.SOLD.value)
        self.min_stories_om.set(RedfinApi.Stories.ONE.value)
        self.min_year_built_om.set(str(self.cur_year - 1))
        self.max_year_built_om.set(str(self.cur_year - 1))
        self.sold_within_om.set(self.sold_within_list[-1])
        self.max_price_om.set(RedfinApi.Price.NONE.value)
        self.min_price_om.set(RedfinApi.Price.NONE.value)
        self.max_sqft_om.set(RedfinApi.Sqft.NONE.value)
        self.min_sqft_om.set(RedfinApi.Sqft.NONE.value)
        self.status_active_chb.deselect()
        self.status_pending_chb.deselect()
        self.status_coming_soon_chb.deselect()
        self.house_type_house_switch.select()
        self.house_type_condo_switch.deselect()
        self.house_type_townhouse_switch.deselect()
        self.house_type_mul_fam_switch.deselect()
        self.status_within_activate_deactivate(self.for_sale_sold_om.get())

    def status_within_activate_deactivate(self, status) -> None:
        """Deactivate or activate the status and sold within sections, since they depend on what type of sale a house is being searched with.

        Args:
            status (Event): ignored
        """
        match self.for_sale_sold_om.get():
            case RedfinApi.SoldStatus.FOR_SALE.value:
                self.sale_status_label.configure(state="normal")
                self.status_active_chb.configure(state="normal")
                self.status_coming_soon_chb.configure(state="normal")
                self.status_pending_chb.configure(state="normal")
                self.sold_within_label.configure(state="disabled")
                self.sold_within_om.configure(state="disabled")
            case RedfinApi.SoldStatus.SOLD.value:
                self.sale_status_label.configure(state="disabled")
                self.status_active_chb.configure(state="disabled")
                self.status_coming_soon_chb.configure(state="disabled")
                self.status_pending_chb.configure(state="disabled")
                self.sold_within_label.configure(state="normal")
                self.sold_within_om.configure(state="normal")
                self.status_active_chb.deselect()
                self.status_pending_chb.deselect()
                self.status_coming_soon_chb.deselect()

    def change_to_search_page(self) -> None:
        """Change to search page."""
        self.grid_remove()
        self.search_page.grid()

    def price_validation(self):
        """Called when price range min om gets changed"""
        if (
            self.max_price_om.get() == RedfinApi.Price.NONE.value
            or self.min_price_om.get() == RedfinApi.Price.NONE.value
        ):
            return
        if int(self.max_price_om.get()) < int(self.min_price_om.get()):
            self.max_price_om.set(self.min_price_om.get())

    def year_validation(self) -> None:
        """Year drop down callback"""
        if int(self.max_year_built_om.get()) < int(self.min_year_built_om.get()):
            self.max_year_built_om.set(self.min_year_built_om.get())

    def sqft_validation(self) -> None:
        """Sqft dropdown callback"""
        if (
            self.max_sqft_om.get() == RedfinApi.Sqft.NONE.value
            or self.min_sqft_om.get() == RedfinApi.Sqft.NONE.value
        ):
            return
        if int(self.max_sqft_om.get()) < int(self.min_sqft_om.get()):
            self.max_sqft_om.set(self.min_sqft_om.get())

    def house_type_validation(self) -> None:
        """House type switch validation to make sure at lest house is selected."""
        if not any(
            [
                self.house_type_house_switch.get(),
                self.house_type_condo_switch.get(),
                self.house_type_mul_fam_switch.get(),
                self.house_type_townhouse_switch.get(),
            ]
        ):
            self.house_type_house_switch.select()

    def get_values(self) -> dict[str, Any]:
        """Get the values of all widgets on this page.

        Returns:
            dict[str, Any]: dict of values
        """
        match self.sold_within_om.get():
            case "Last 1 week":
                sold_within_days = RedfinApi.SoldWithinDays.ONE_WEEK
            case "Last 1 month":
                sold_within_days = RedfinApi.SoldWithinDays.ONE_MONTH
            case "Last 3 months":
                sold_within_days = RedfinApi.SoldWithinDays.THREE_MONTHS
            case "Last 6 months":
                sold_within_days = RedfinApi.SoldWithinDays.SIX_MONTHS
            case "Last 1 year":
                sold_within_days = RedfinApi.SoldWithinDays.ONE_YEAR
            case "Last 2 years":
                sold_within_days = RedfinApi.SoldWithinDays.TWO_YEARS
            case "Last 3 years":
                sold_within_days = RedfinApi.SoldWithinDays.THREE_YEARS
            case _:
                sold_within_days = RedfinApi.SoldWithinDays.FIVE_YEARS

        return {
            "for sale sold": self.for_sale_sold_om.get(),
            "min stories": self.min_stories_om.get(),
            "max year built": self.max_year_built_om.get(),  # do validation here
            "min year built": self.min_year_built_om.get(),
            "sold within": sold_within_days.value,
            "status active": bool(self.status_active_chb.get()),
            "status coming soon": bool(self.status_coming_soon_chb.get()),
            "status pending": bool(self.status_pending_chb.get()),
            "house type house": bool(self.house_type_house_switch.get()),
            "house type townhouse": bool(self.house_type_townhouse_switch.get()),
            "house type mul fam": bool(self.house_type_mul_fam_switch.get()),
            "house type condo": bool(self.house_type_condo_switch.get()),
            "max sqft": self.max_sqft_om.get(),
            "min sqft": self.min_sqft_om.get(),
            "max price": self.max_price_om.get(),
            "min price": self.min_price_om.get(),
        }
