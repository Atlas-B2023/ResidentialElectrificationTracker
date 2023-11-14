# import polars as pl
# from backend import Helper
# from backend.us import states as sts
from gui import app
# from backend.SecondaryData import CensusAPI

# from backend.RedfinSearcher import RedfinSearcher as rfs

if __name__ == "__main__":
    gui_app = app.App()
    gui_app.mainloop()
    # state = sts.lookup("MS")
    # print(Helper.get_census_report_url_page(state.name))
    # c = CensusAPI()
    # print(c.get_acs5_subject_table_group_for_zcta_by_year("S1901", "2019"))
    # print(c.get_acs5_profile_table_group_for_zcta_by_year("DP05", "2019"))
