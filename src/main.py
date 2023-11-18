# import polars as pl
# from backend import helper
# from backend.us import states as sts
# from backend.secondarydata import EIADataRetriever
from backend.redfinscraper import RedfinApi
# import datetime
# from gui import app


if __name__ == "__main__":
    # gui_app = app.App()
    # gui_app.mainloop()
    rfs = RedfinApi()
    rfs.get_house_attributes_from_metro(
        "TEST",
        "2022",
        "2023",
        RedfinApi.Stories.ONE,
        RedfinApi.SortOrder.MOST_RECENTLY_SOLD,
        [RedfinApi.HouseType.HOUSE],
        RedfinApi.SoldWithinDays.FIVE_YEARS,
    )
