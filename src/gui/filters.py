# import tkinter as tk
# from tkinter import ttk
import customtkinter as ctk

# exercise:
# convert the app to use ctk


# s1=swich1.get()
# def converts():
# print(entry.get())
# def inSoldChange(self,x)
#     if


class FiltersPage(ctk.CTkFrame)):
    def __init__(self):
        # main setup
        super().__init__()
        self.title("Filter")
        self.geometry("400x600")
        self.minsize(400, 600)
        self.maxsize(400, 600)
        self.rowconfigure((0, 2), weight=1)
        self.columnconfigure((0, 2), weight=1)
        self.rowconfigure(1, weight=30)
        self.columnconfigure(1, weight=30)

        self.create_widgets()

    # widgets

    # run

    def create_widgets(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=1, column=1)
        frame.columnconfigure((0), weight=1, uniform="a")
        frame.rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10), weight=1, uniform="a")
        forsale_sold = ctk.CTkFrame(
            frame, width=300, height=100, fg_color="transparent"
        )
        Stories = ctk.CTkFrame(frame)
        year_build = ctk.CTkFrame(frame, fg_color="transparent")
        home_type = ctk.CTkFrame(frame)
        square_feet = ctk.CTkFrame(frame, fg_color="transparent")
        status = ctk.CTkFrame(frame)
        sold_within = ctk.CTkFrame(frame, fg_color="transparent")
        price_range = ctk.CTkFrame(frame)
        resetfilter_applyfilter = ctk.CTkFrame(frame, fg_color="transparent")

        # placing the frames
        forsale_sold.grid(row=0, column=0, columnspan=1, sticky="nsew")
        Stories.grid(row=1, column=0, sticky="nesw")
        year_build.grid(row=2, column=0, rowspan=1, sticky="nesw")
        home_type.grid(row=3, column=0, rowspan=2, sticky="nesw")
        square_feet.grid(row=5, column=0, rowspan=1, sticky="nesw")
        status.grid(row=6, column=0, rowspan=1)
        sold_within.grid(row=7, column=0, sticky="nesw")
        price_range.grid(row=8, column=0, rowspan=2, sticky="nesw")
        resetfilter_applyfilter.grid(row=10, column=0)

        # make more grid
        forsale_sold.columnconfigure((0, 1), weight=1)
        forsale_sold.rowconfigure(0, weight=1)
        Stories.columnconfigure((0, 1), weight=1)
        Stories.rowconfigure(0, weight=1)
        year_build.columnconfigure((0, 1, 2, 3), weight=1)
        year_build.rowconfigure((0, 1), weight=1)
        home_type.columnconfigure((0, 1, 2, 3), weight=1)
        home_type.rowconfigure((0, 1, 2), weight=1)
        square_feet.columnconfigure((0, 1, 2, 3), weight=1)
        square_feet.rowconfigure((0, 1), weight=1)
        status.columnconfigure((0, 1, 2), weight=1)
        status.rowconfigure((0, 1), weight=1)
        sold_within.columnconfigure((0, 1), weight=1)
        sold_within.rowconfigure(0, weight=1)
        price_range.columnconfigure((0, 1, 2, 3), weight=1)
        price_range.rowconfigure((0, 1), weight=1)
        resetfilter_applyfilter.columnconfigure((0, 1), weight=1)
        resetfilter_applyfilter.rowconfigure(0, weight=1)

        # Create the labels
        Label1 = ctk.CTkLabel(forsale_sold, text="For Sale/Sold")
        Label2 = ctk.CTkLabel(Stories, text="Stories")
        Label3 = ctk.CTkLabel(year_build, text="Year Build")
        Label4 = ctk.CTkLabel(home_type, text="Home Type")
        Label5 = ctk.CTkLabel(square_feet, text="Square Feet")
        Label6 = ctk.CTkLabel(status, text="Sold Within")
        Label7 = ctk.CTkLabel(price_range, text="Price Range")
        Label8 = ctk.CTkLabel(year_build, text="From")
        Label9 = ctk.CTkLabel(year_build, text="To")
        Label10 = ctk.CTkLabel(price_range, text="From")
        Label11 = ctk.CTkLabel(price_range, text="To")
        Label12 = ctk.CTkLabel(sold_within, text="Sold Within")
        Label13 = ctk.CTkLabel(square_feet, text="From")
        Label14 = ctk.CTkLabel(square_feet, text="To")

        self.sold_within_labels = [
            "Last 1 week",
            "Last 1 month",
            "Last 3 months",
            "Last 6 months",
            "Last 1 year",
            "Last 2 years",
            "Last 3 years",
            "Last 4 years",
            "Last 5 years",
        ]
        # Create the Buttons
        combobox1 = ctk.CTkComboBox(
            master=forsale_sold, values=["For sale", "For sold"]
        )
        combobox2 = ctk.CTkComboBox(Stories, values=["1", "2", "3", "4", "5", "6"])
        combobox3 = ctk.CTkComboBox(
            year_build, values=[str(x) for x in range(1960, 2022)]
        )
        combobox4 = ctk.CTkComboBox(
            year_build, values=[str(x) for x in range(1960, 2022)]
        )
        switch1 = ctk.CTkSwitch(home_type, text="House")
        switch2 = ctk.CTkSwitch(home_type, text="Townhouse")
        switch3 = ctk.CTkSwitch(home_type, text="Condo")
        switch4 = ctk.CTkSwitch(home_type, text="Multi-Family")
        combobox5 = ctk.CTkComboBox(
            square_feet,
            values=[
                "500",
                "750",
                "1000",
                "1250",
                "1500",
                "1750",
                "2000",
                "2250",
                "2500",
                "2750",
                "3000",
            ],
        )
        combobox6 = ctk.CTkComboBox(
            square_feet,
            values=[
                "500",
                "750",
                "1000",
                "1250",
                "1500",
                "1750",
                "2000",
                "2250",
                "2500",
                "2750",
                "3000",
            ],
        )
        checkbox1 = ctk.CTkCheckBox(status, text="Coming soon")
        checkbox2 = ctk.CTkCheckBox(status, text="Active")
        checkbox3 = ctk.CTkCheckBox(status, text="Under contract/Pending")
        combobox7 = ctk.CTkComboBox(sold_within, values=self.sold_within_labels)
        combobox8 = ctk.CTkComboBox(
            price_range,
            values=[
                "100k",
                "150k",
                "200k",
                "250k",
                "300k",
                "350k",
                "400k",
                "450k",
                "500k",
                "550k",
                "600k",
                "700k",
                "750k",
                "800k",
                "850k",
                "900k",
                "950k",
                "1M",
            ],
        )
        combobox9 = ctk.CTkComboBox(
            price_range,
            values=[
                "100k",
                "150k",
                "200k",
                "250k",
                "300k",
                "350k",
                "400k",
                "450k",
                "500k",
                "550k",
                "600k",
                "700k",
                "750k",
                "800k",
                "850k",
                "900k",
                "950k",
                "1M",
            ],
        )
        button1 = ctk.CTkButton(resetfilter_applyfilter, text="Reset Filters")
        button2 = ctk.CTkButton(resetfilter_applyfilter, text="Apply Filters")

        # Placing the weidgets
        Label1.grid(row=0, column=0)
        Label2.grid(row=0, column=0)
        Label3.grid(row=0, column=0)
        Label4.grid(row=0, column=0)
        Label5.grid(row=0, column=0)
        Label6.grid(row=0, column=0)
        Label7.grid(row=0, column=0)
        Label8.grid(row=1, column=0)
        Label9.grid(row=1, column=2)
        Label10.grid(row=1, column=0)
        Label11.grid(row=1, column=2)
        Label12.grid(row=0, column=0)
        Label13.grid(row=1, column=0)
        Label14.grid(row=1, column=2)

        combobox1.grid(row=0, column=1)
        combobox2.grid(row=0, column=1)
        combobox3.grid(row=1, column=1)
        combobox4.grid(row=1, column=3)
        combobox5.grid(row=1, column=1)
        combobox6.grid(row=1, column=3)
        combobox7.grid(row=0, column=1)
        combobox8.grid(row=1, column=1)
        combobox9.grid(row=1, column=3)
        switch1.grid(row=1, column=0)
        switch2.grid(row=1, column=1)
        switch3.grid(row=2, column=0)
        switch4.grid(row=2, column=1)
        checkbox1.grid(row=1, column=0)
        checkbox2.grid(row=1, column=1)
        checkbox3.grid(row=1, column=2)
        button1.grid(row=0, column=0, sticky="nesw")
        button2.grid(row=0, column=1, sticky="nesw")


FiltersPage().mainloop()
