# import polars as pl
# from backend import Helper
# from backend.us import states as sts
# from backend.SecondaryData import EIADataRetriever
# import datetime
from gui import app


if __name__ == "__main__":
    gui_app = app.App()
    gui_app.mainloop()

    # eia = EIADataRetriever()
    # energy_btu = eia.monthly_price_per_million_btu_by_energy_type_by_state(
    #     "CA",
    #     datetime.date(2022, 1, 1),
    #     datetime.date(2023, 1, 1),
    # )
    # print(energy_btu)
    # state = sts.lookup("MS")
    # print(Helper.get_census_report_url_page(state.name))
    # c = CensusAPI()
    # print(c.get_acs5_subject_table_group_for_zcta_by_year("S1901", "2019"))
    # print(c.get_acs5_profile_table_group_for_zcta_by_year("DP05", "2019"))
