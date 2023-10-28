from searcher import RedfinSearcher
from helper import Sort, PropertyType, Include, Stories
import polars as pl

redfin_searcher = RedfinSearcher()

filters_path = redfin_searcher.generate_filters_path(
    sort=Sort.MOST_RECENT_SOLD,
    property_type=PropertyType.HOUSE,
    min_year_built=2022,
    max_year_built=2022,
    include=Include.LAST_5_YEAR,
    min_stories=Stories.ONE,
)
# have in constructor, setter, and use setter in load house attributes
house_data_df = redfin_searcher.load_house_attributes_from_metro("TEST", filters_path)
# house_data_df = redfin_searcher.load_house_attributes_from_metro(55424, filters_path)

with pl.Config(tbl_cols=10):
    print(house_data_df)
