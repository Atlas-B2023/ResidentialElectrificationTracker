from searcher import RedfinSearcher
import polars as pl

# TODO test this snippet
redfin_searcher = RedfinSearcher(
    filters_path=RedfinSearcher.generate_filters_path(
        sort=RedfinSearcher.Sort.MOST_RECENT_SOLD,
        property_type=RedfinSearcher.PropertyType.HOUSE,
        min_year_built=2022,
        max_year_built=2022,
        include=RedfinSearcher.Include.LAST_5_YEAR,
        min_stories=RedfinSearcher.Stories.ONE,
    )
)

house_data_df = redfin_searcher.load_house_attributes_from_metro("TEST")

with pl.Config(tbl_cols=10):
    print(house_data_df)
