# import polars as pl
# from backend import helper
# from backend.us import states as sts
# from backend.secondarydata import EIADataRetriever
from backend.redfinscraper import NewScraper
# import datetime
# from gui import app


if __name__ == "__main__":
    # gui_app = app.App()
    # gui_app.mainloop()
    rfs = NewScraper()
    print(
        rfs.get_gis_csv_for_zips_in_metro_with_filters(
            "TEST",
            "2022",
            "2023",
            NewScraper.Stories.ONE,
            NewScraper.SortOrder.MOST_RECENTLY_SOLD,
            [NewScraper.HouseType.HOUSE],
            NewScraper.SoldWithinDays.FIVE_YEARS,
        )
    )
