import requests
from bs4 import BeautifulSoup as btfs
import polars as pl
import helper
import listing_scraper
from enum import StrEnum


# PURPOSE: this file

# this will probably be called by main. will need a dataframe parameter?
# all urls in code will not have a trailing forward slash in urls
# can either preform url checks before, or wait until everything is formed and do lots of path tracing when we bounce from the endpoint


# look at ways to decuple this class from redfin?
class RedfinSearcher:
    def __init__(self) -> None:
        self.REDFIN_BASE_URL = "https://www.redfin.com"
        self.LISTING_SCHEMA = {
            "LATITUDE": pl.Float32,
            "LONGITUDE": pl.Float32,
            "ADDRESS": str,
            "CITY": str,
            "STATE OR PROVINCE": str,
            "ZIP OR POSTAL CODE": pl.UInt16,
            "PRICE": pl.UInt32,
            "YEAR BUILT": pl.UInt16,
            "SQUARE FEET": pl.UInt32,
            "HEATING AMENITIES": list[str],
        }
        self.FULL_CSV_SCHEMA = {
            "SALE TYPE": pl.Utf8,
            "SOLD DATE": pl.Utf8,
            "PROPERTY TYPE": pl.Utf8,
            "ADDRESS": pl.Utf8,
            "CITY": pl.Utf8,
            "STATE OR PROVINCE": pl.Utf8,
            "ZIP OR POSTAL CODE": pl.UInt16,
            "PRICE": pl.UInt32,
            "BEDS": pl.UInt8,
            "BATHS": pl.Float32,
            "LOCATION": pl.Utf8,
            "SQUARE FEET": pl.UInt32,
            "LOT SIZE": pl.UInt32,
            "YEAR BUILT": pl.UInt16,
            "DAYS ON MARKET": pl.UInt32,
            "$/SQUARE FEET": pl.Float32,
            "HOA/MONTH": pl.Float32,
            "STATUS": pl.Utf8,
            "NEXT OPEN HOUSE START TIME": pl.Utf8,
            "NEXT OPEN HOUSE END TIME": pl.Utf8,
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)": pl.Utf8,
            "SOURCE": pl.Utf8,
            "MLS#": pl.Utf8,
            "FAVORITE": pl.Utf8,
            "INTERESTED": pl.Utf8,
            "LATITUDE": pl.Float32,
            "LONGITUDE": pl.Float32,
        }
        self.CSV_SCHEMA = {
            "ADDRESS": str,
            "CITY": str,
            "STATE OR PROVINCE": str,
            "YEAR BUILT": pl.UInt16,
            "ZIP OR POSTAL CODE": pl.UInt16,
            "PRICE": pl.UInt32,
            "SQUARE FEET": pl.UInt32,
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)": str,
            "LATITUDE": pl.Float32,
            "LONGITUDE": pl.Float32,
        }

    class PropertyType(StrEnum):
        HOUSE = "house"
        CONDO = "condo"
        TOWNHOUSE = "townhouse"
        LAND = "land"
        OTHER = "other"
        MANUFACTURED = "manufactured"
        COOP = "co-op"
        MULTIFAMILY = "multifamily"

    class Status(StrEnum):
        ACTIVE = "active"
        COMINGSOON = "comingsoon"
        CONTINGENT = "contingent"
        PENDING = "pending"

    class Include(StrEnum):
        """Sold times are cumulative. When sorting by last sold, the houses that
        show up in the 1 week search will be the first ones to show up in the last 1 year search, for example
        """

        LAST_1_WEEK = "sold-1wk"
        LAST_1_MONTH = "sold-1mo"
        LAST_3_MONTHS = "sold-3mo"
        LAST_6_MONTHS = "sold-6mo"
        LAST_1_YEAR = "sold-1yr"
        LAST_2_YEAR = "sold-2yr"
        LAST_3_YEAR = "sold-3yr"
        LAST_5_YEAR = "sold-5yr"

    class Stories(StrEnum):
        ONE = "1"
        TWO = "2"
        THREE = "3"
        FOUR = "4"
        FIVE = "5"
        TEN = "10"
        FIFTEEN = "15"
        TWENTY = "20"

    class Sqft(StrEnum):
        SEVEN_FIFTY = "750"
        THOU = "1K"
        THOU_1 = "1.1k"
        THOU_2 = "1.2k"
        THOU_3 = "1.3k"
        THOU_4 = "1.4k"
        THOU_5 = "1.5k"
        THOU_6 = "1.6k"
        THOU_7 = "1.7k"
        THOU_8 = "1.8k"
        THOU_9 = "1.9k"
        TWO_THOU = "2k"
        TWO_THOU_250 = "2.25k"
        TWO_THOU_500 = "2.5k"
        TWO_THOU_750 = "2.75k"
        THREE_THOU = "3k"
        FOUR_THOU = "4k"
        FIVE_THOU = "5k"
        SEVEN_THOU_500 = "7.5k"
        TEN_THOU = "10k"

    class Sort(StrEnum):
        # for sale only
        NEWEST = "lo-days"
        # sold only
        MOST_RECENT_SOLD = "hi-sale-date"
        LOW__TO_HIGH_PRICE = "lo-price"
        HIGH_TO_LOW_PRICE = "hi-price"
        SQFT = "hi-sqft"
        LOT_SIZE = "hi-lot-sqf"
        PRICE_PER_SQFT = "lo-dollarsqft"

    def _generate_area_path(self, zip_code_or_city_and_state_or_address: str) -> str:
        """Generates the path for a location

        Args:
            zip_code_or_city_and_state_or_address (str): the location, either a zip code, or a city and state, or an address

        Returns:
            path: the path, for example "/zipcode/01609"
        """
        # save on a request?. have to really check where zips are being treated as strings and ints
        if (
            len(zip_code_or_city_and_state_or_address) == 5
            and zip_code_or_city_and_state_or_address.isdigit()
        ):
            return f"/zipcode/{zip_code_or_city_and_state_or_address}"
        return f"{helper.get_redfin_url_path(zip_code_or_city_and_state_or_address)}"

    def _generate_filter_path(self, **kwargs) -> str:
        """Generates the path for given filters. Available filters are listed below, and values can be found in the enums in this class.

        Returns:
            str: the url path, for example "/min-story=1,min-year-built=2023"
        """
        # available_filters = [
        #     "include",
        #     "property-type",
        #     "min-beds",
        #     "max-beds",
        #     "min-baths",
        #     "max-baths",
        #     "min-year-built",
        #     "max-year-built",
        #     "status",
        #     "min-price",
        #     "max-price",
        #     "sort",
        #     "exclude-age-restricted",
        #     "is-green",
        #     "fireplace",
        # ]
        selected_filters = []

        # can do additional checks if wanted, treat param names as filter words
        for key, value in kwargs.items():
            if isinstance(value, list):
                selected_filters.append(f'{key.replace("_","-")}={"+".join(value)}')
            else:
                selected_filters.append(f'{key.replace("_","-")}={value}')

        return f'/filter/{",".join(selected_filters)}'

    def _df_from_search_page_csv(self, url: str) -> pl.DataFrame | None:
        """Returns a modified format of the search page csv from the given search page url.

        Args:
            url (str): url of search page

        Returns:
            pl.DataFrame: dataframe in format of "ADDRESS","CITY","STATE OR PROVINCE","YEAR BUILT","ZIP OR POSTAL CODE",
            "PRICE","SQUARE FEET","URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
            "LATITUDE","LONGITUDE"
        """

        req = helper.req_get_wrapper(url)
        req.raise_for_status()

        html = req.content
        soup = btfs(html, "html.parser")
        download_button_id = "download-and-save"
        download_link_tag = soup.find("a", id=download_button_id)
        if download_link_tag is None:
            # should be handled in caller
            raise TypeError(
                "Could not find csv download. Check if the html downloaded is correct, or if the download button id has changed"
            )

        download_link = download_link_tag.get("href")

        match download_link:
            case None:
                raise KeyError(
                    f"<a> tag with id {download_button_id} does not exist. Has the HTML id changed?"
                )
            case list():
                raise KeyError(
                    f"<a> tag with id {download_button_id} has multiple values"
                )

        df = pl.read_csv(
            source=f"{self.REDFIN_BASE_URL}{download_link}", dtypes=self.FULL_CSV_SCHEMA
        )

        return df.select(
            "ADDRESS",
            "CITY",
            "STATE OR PROVINCE",
            "YEAR BUILT",
            "ZIP OR POSTAL CODE",
            "PRICE",
            "SQUARE FEET",
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
            "LATITUDE",
            "LONGITUDE",
        )

    def _zips_to_search_page_csvs(
        self, zip_codes: list[int], filters_path: str
    ) -> pl.DataFrame | None:
        """Takes in a list of zip codes and returns a dataframe produced by concatenating all of the zip codes' search page csvs.

        Args:
            zip_codes (list[int]): list of zip codes to search
            filters_path (str): the filters to search the zip codes with

        Returns:
            pl.DataFrame | None: the dataframe of all of the csvs concatenated into one dataframe
        """
        formatted_zip_codes = [f"{zip_code:0{5}}" for zip_code in zip_codes]
        list_of_csv_dfs = []

        for zip_code in formatted_zip_codes:
            url = f"{self.REDFIN_BASE_URL}{self._generate_area_path(zip_code)}{filters_path}"

            try:
                # this is the only place where this error should pop up. if a zip is invalid,
                # return none and handle in caller. an example is the zip 56998, which is just a
                # USPS distribution center in D.C
                # should df_from_search_page be returning none
                redfin_csv_df = self._df_from_search_page_csv(url)
            except requests.HTTPError:
                print("Invalid zip")
                return None

            if redfin_csv_df is None:
                print(
                    f"{zip_code} did not return any matching houses with the given filters"
                )
                return None

            list_of_csv_dfs.append(redfin_csv_df)
        return pl.concat(list_of_csv_dfs)

    def load_house_attributes_from_metro(
        self, metro_name: str, filters_path: str
    ) -> pl.DataFrame:
        zip_codes = helper.metro_name_to_zip_code_list(metro_name)

        if len(zip_codes) == 0:
            return pl.DataFrame(schema=self.LISTING_SCHEMA)

        zip_code_search_page_csvs_df = self._zips_to_search_page_csvs(
            zip_codes, filters_path
        )
        if zip_code_search_page_csvs_df is None:
            print("No supplied zip code has housing data available")
            return pl.DataFrame(schema=self.LISTING_SCHEMA)
        
        house_attribs_df = self.listing_attributes_from_search_page_csv(zip_code_search_page_csvs_df)
        
        if house_attribs_df is None:
            print("No houses in the supplied zip code have housing data")
            return pl.DataFrame(schema=self.LISTING_SCHEMA)
        # house atrivs check
        return house_attribs_df

    def listing_attributes_from_search_page_csv(
        self, search_page_csvs: pl.DataFrame
    ) -> pl.DataFrame | None:
        listing_dfs_to_concat = []

        # all houses that meet criteria are in this df
        #will url(...) always be there? might want to null check and throw out nulls in the search page csv func
        for listing in search_page_csvs.rows(named=True):
            listing_heating_amenities_dict = listing_scraper.heating_amenities_scraper(
                listing[
                    "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
                ]
            )
            #! this list conversion should be done in the helper method. really hacky
            listing_heating_amenities_list = []
            for key in listing_heating_amenities_dict.keys():
                listing_heating_amenities_list.append(key)
                listing_heating_amenities_list.append(
                    listing_heating_amenities_dict.get(key)
                )

            if len(listing_heating_amenities_list) == 0:
                print(
                    f"House {listing['ADDRESS']} does not have heating information available. Skipping..."
                )
                continue

            # look into making heating amenities a list of strings, better for dataframe
            listing_info_dict = {
                "LATITUDE": listing["LATITUDE"],
                "LONGITUDE": listing["LONGITUDE"],
                "ADDRESS": listing["ADDRESS"],
                "CITY": listing["CITY"],
                "STATE OR PROVINCE": listing["STATE OR PROVINCE"],
                "ZIP OR POSTAL CODE": listing["ZIP OR POSTAL CODE"],
                "PRICE": listing["PRICE"],
                "YEAR BUILT": listing["YEAR BUILT"],
                "SQUARE FEET": listing["SQUARE FEET"],
                "HEATING AMENITIES": [listing_heating_amenities_list],
            }
            listing_dfs_to_concat.append(
                pl.DataFrame(listing_info_dict, schema=self.LISTING_SCHEMA)
            )
            print(f"Adding {listing_info_dict['ADDRESS']} to list.")

        return pl.concat(listing_dfs_to_concat, how="vertical_relaxed")


if __name__ == "__main__":
    s = RedfinSearcher()
    with pl.Config(tbl_cols=10):
        print(
            s._zips_to_search_page_csvs(
                [22066, 55424],
                s._generate_filter_path(
                    sort=s.Sort.MOST_RECENT_SOLD,
                    property_type=s.PropertyType.HOUSE,
                    min_year_built=2022,
                    max_year_built=2022,
                    include=s.Include.LAST_5_YEAR,
                    min_stories=s.Stories.ONE,
                ),
            )
        )
