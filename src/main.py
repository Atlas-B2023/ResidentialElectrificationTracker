# import polars as pl
from gui import app
# from backend.SecondaryData import CensusAPI

# from backend.RedfinSearcher import RedfinSearcher as rfs

if __name__ == "__main__":
    # redfin_searcher = rfs(
    #     filters_path=rfs.generate_filters_path(
    #         sort=rfs.Sort.MOST_RECENTLY_SOLD,
    #         property_type=rfs.PropertyType.HOUSE,
    #         min_year_built=2022,
    #         max_year_built=2022,
    #         include=rfs.Include.LAST_5_YEAR,
    #         min_stories=rfs.Stories.ONE,
    #     )
    # )
    # # takes about 1.7 seconds per listing
    # house_data_df = redfin_searcher.load_house_attributes_from_metro(
    #     "Youngstown-Warren-Boardman, OH-PA"
    # )
    # with pl.Config(tbl_cols=-1):
    #     print(house_data_df)
    #     if house_data_df.height != 0:
    #         Helper.df_to_file(house_data_df)
    gui_app = app.App()
    gui_app.mainloop()
    # print(Helper.metro_name_to_zip_code_list("Jackson County, AL"))

    # c = CensusAPI()
    # c.get_table_group_for_zcta_by_state_by_year("DP05", "2019", "california")
