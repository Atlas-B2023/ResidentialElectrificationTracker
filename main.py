import searcher
from helper import *
import listing_scraper

base_url = "https://redfin.com"
area_path = searcher.generate_area_path("75220")
filters_path = searcher.generate_filter_path(
    sort=Sort.MOST_RECENT_SOLD,
    property_type=PropertyType.HOUSE,
    min_year_built=2022,
    max_year_built=2022,
    include=Include.LAST_3_YEAR,
)
search_page_url = base_url + area_path + filters_path

df = searcher.csv_from_search_page_url(search_page_url)

listings = df[
    "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
]
#.map_elements(listing_scraper.heating_amenities_scraper)

for listing in listings:
    print(listing_scraper.heating_amenities_scraper(listing))
