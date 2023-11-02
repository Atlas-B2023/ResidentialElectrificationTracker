import polars as pl
import Helper
from RedfinSearcher import RedfinSearcher as rfs

if __name__ == "__main__":
    redfin_searcher = rfs(
        filters_path=rfs.generate_filters_path(
            sort=rfs.Sort.MOST_RECENTLY_SOLD,
            property_type=rfs.PropertyType.HOUSE,
            min_year_built=2022,
            max_year_built=2022,
            include=rfs.Include.LAST_5_YEAR,
            min_stories=rfs.Stories.ONE,
        )
    )
    # takes about 1.7 seconds per listing
    house_data_df = redfin_searcher.load_house_attributes_from_metro("Niles, MI")
    with pl.Config(tbl_cols=-1):
        print(house_data_df)
        if house_data_df.height != 0:
            Helper.df_to_file(house_data_df)
