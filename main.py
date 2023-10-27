# import searcher
# from helper import *
# import listing_scraper

# #redfin flow
# base_url = "https://redfin.com"
# area_path = searcher.generate_area_path("75220")
# filters_path = searcher.generate_filter_path(
#     sort=Sort.MOST_RECENT_SOLD,
#     property_type=PropertyType.HOUSE,
#     min_year_built=2022,
#     max_year_built=2022,
#     include=Include.LAST_3_YEAR,
# )
# search_page_url = base_url + area_path + filters_path

# df = searcher.csv_from_search_page_url(search_page_url)

# for listing in df.rows(named=True):
#     print(f"{listing["LATITUDE"]}, {listing["LONGITUDE"]}, {listing["ADDRESS"]}, {listing["STATE OR PROVINCE"]}, {listing["ZIP OR POSTAL CODE"]}, {listing["PRICE"]}, {listing["YEAR BUILT"]}, {listing["SQUARE FEET"]}, {listing["LOT SIZE"]}, {listing_scraper.heating_amenities_scraper(listing["URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"])}")

from searcher import RedfinSearcher
from helper import Sort, PropertyType, Include, Stories
import polars as pl

redfin_searcher = RedfinSearcher()

filters_path = redfin_searcher._generate_filter_path(
    sort=Sort.MOST_RECENT_SOLD,
    property_type=PropertyType.HOUSE,
    min_year_built=2022,
    max_year_built=2022,
    include=Include.LAST_5_YEAR,
    min_stories=Stories.ONE,
)

house_data_df = redfin_searcher.load_house_attributes_from_metro("TEST", filters_path)
# house_data_df = redfin_searcher.load_house_attributes_from_metro(55424, filters_path)

with pl.Config(tbl_cols=10, tbl_rows=25):
    print(house_data_df.head(25))
