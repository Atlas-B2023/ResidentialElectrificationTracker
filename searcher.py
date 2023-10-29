import requests
from bs4 import BeautifulSoup as btfs
import polars as pl
import helper
import listing_scraper
from enum import StrEnum
from datetime import datetime, timedelta

# PURPOSE: this file

# this will probably be called by main. will need a dataframe parameter?
# all urls in code will not have a trailing forward slash in urls
# can either preform url checks before, or wait until everything is formed and do lots of path tracing when we bounce from the endpoint


# look at ways to decuple this class from redfin?
class RedfinSearcher:
    """A class that scrapes and Redfin, while also using their stingray API for getting information about houses on Redfin.

    Usage
    -----
    >>> rfs = RedfinSearcher()
    >>> filters = rfs.generate_filters_path(...)
    >>> rfs.set_filters_path(filters)
    """

    def __init__(self, filters_path: str | None = None) -> None:
        self.REDFIN_BASE_URL = "https://www.redfin.com"
        if filters_path is None:
            self.filters_path = self.generate_filters_path(
                sort=self.Sort.MOST_RECENT_SOLD,
                property_type=self.PropertyType.HOUSE,
                min_year_built=(datetime.now() - timedelta(weeks=52 * 5)).year,
                include=self.Include.LAST_5_YEAR,
                min_stories=self.Stories.ONE,
            )
        else:
            self.filters_path = filters_path
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
        self.logger = helper.logger

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

    def set_filters_path(self, filters_path: str) -> None:
        """Set the search filters for all searchers made with this RedfinSearcher object.

        Args:
            filters_path (str): the URL path to search with
        """
        self.logger.debug(f"Setting filters to: {filters_path}")
        self.filters_path = filters_path

    def _generate_area_path(self, zip_code_or_city_and_state_or_address: str) -> str:
        """Generates the path for a location. Redfin uses proprietary numbers to identify cities. This makes a call to their
        stingray API to get the translation.

        Args:
            zip_code_or_city_and_state_or_address (str): the location. Either a zip code, or a city and state, or an address

        Returns:
            path: the path, for example "/zipcode/01609"
        """
        if (
            len(zip_code_or_city_and_state_or_address) == 5
            and zip_code_or_city_and_state_or_address.isdigit()
        ):
            return f"/zipcode/{zip_code_or_city_and_state_or_address}"

        # Cache this to a json or something
        path_url = (
            f"{helper.get_redfin_url_path(zip_code_or_city_and_state_or_address)}"
        )
        return path_url

    @staticmethod
    def generate_filters_path(**kwargs) -> str:
        """Generates the path for given filters. Note that some filters cannot be used together

        Available filters
        -----------------
            * ``include``
            * ``property-type``
            * ``min-beds``
            * ``max-beds``
            * ``min-baths``
            * ``max-baths``
            * ``min-year-built``
            * ``max-year-built``
            * ``status``
            * ``min-price``
            * ``max-price``
            * ``sort``
            * ``exclude-age-restricted``
            * ``is-green``
            * ``fireplace``
            * ``min-stories``
            * ``min-sqft``

        Example
        -------
        For generating a filter string that has a filter with 1 value:

        >>> generate_filters_path(min-sqft=Sqft.THOU, property_type=PropertyType.HOUSE)
        "/filter/min-sqft=1k,property-type=house"

        For generating a filter string that has a filter with multiple values:

        >>> generate_filters_path(min-sqft=Sqft.THOU, property_type=[PropertyType.HOUSE, PropertyType.TOWNHOUSE])
        "/filter/min-sqft=1k,property-type=house+townhouse"

        Exclusions
        ----------
        When searching by sold, you cannot use: TODO

        When searching by for-sale, you cannot use: TODO

        Returns:
            str: the url filter string
        """
        selected_filters = []

        # can do additional checks if wanted, treat param names as filter words
        for key, value in kwargs.items():
            if isinstance(value, list):
                selected_filters.append(f'{key.replace("_","-")}={"+".join(value)}')
            else:
                selected_filters.append(f'{key.replace("_","-")}={value}')

        return f'/filter/{",".join(selected_filters)}'

    def _df_from_search_page_csv(self, url: str) -> pl.DataFrame | None:
        """Returns a DataFrame of the contents scraped from the download button from the specified search page URL. The schema of this DataFrame is listed in ``RedfinSearcher.CSV_SCHEMA``.

        Args:
            url (str): the URL of the search page

        Returns:
            pl.DataFrame | None: the DataFrame. Is empty if there are no listings for the given filters. Is None if the CSV download link is not available
        """
        req = helper.req_get_wrapper(url)
        req.raise_for_status()

        html = req.content
        soup = btfs(html, "html.parser")
        download_button_id = "download-and-save"
        download_link_tag = soup.find("a", id=download_button_id)
        if download_link_tag is None:
            # should be handled in caller
            # randomly gives this error. investigate, if truly just random, retry in one second
            self.logger.debug(
                f"Finding download button failed for {url = }. {req.status_code = }, {len(html) = }"
            )
            raise TypeError(
                "Could not find CSV download. Check if the html downloaded is correct, or if the download button id has changed"
            )

        download_link = download_link_tag.get("href")  # type: ignore

        match download_link:
            case None:
                raise KeyError(
                    f"<a> tag with id {download_button_id} does not exist. Has the HTML id changed?"
                )
            case list():
                raise KeyError(
                    f"<a> tag with id {download_button_id} has multiple values"
                )

        return pl.read_csv(
            source=f"{self.REDFIN_BASE_URL}{download_link}", dtypes=self.FULL_CSV_SCHEMA
        ).select(
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

    def _zips_to_search_page_csvs(self, zip_codes: list[int]) -> pl.DataFrame | None:
        """Returns a DataFrame produced by concatenating all of the specified ZIP codes' search page CSVs.

        Args:
            zip_codes (list[int]): list of ZIP codes to search

        Returns:
            pl.DataFrame | None: the concatenated DataFrame. Is empty if there are no listings for the given filters. Is None if the CSV download link is not available
        """
        formatted_zip_codes = [f"{zip_code:0{5}}" for zip_code in zip_codes]
        list_of_csv_dfs = []

        for zip_code in formatted_zip_codes:
            search_page_url = f"{self.REDFIN_BASE_URL}{self._generate_area_path(zip_code)}{self.filters_path}"
            self.logger.debug(f"searching zip code with {search_page_url = }")
            try:
                # this is the only place where this error should pop up. if a zip is invalid,
                # return none and handle in caller. an example is the zip 56998, which is just a
                # USPS distribution center in D.C
                # should df_from_search_page be returning none
                redfin_csv_df = self._df_from_search_page_csv(search_page_url)
            except requests.HTTPError as e:
                #! this also gave random error
                self.logger.error(
                    f"{search_page_url = } gave an invalid zip code (possible its something else) error.\n{e}"
                )
                return None

            if redfin_csv_df is None:
                self.logger.info(
                    f"The download link for {zip_code}'s search page is not available"
                )
                continue

            list_of_csv_dfs.append(redfin_csv_df)
        return pl.concat(list_of_csv_dfs)

    def load_house_attributes_from_metro(
        self, metro_name: str, filters_path: str | None = None
    ) -> pl.DataFrame:
        """Produces a DataFrame of a metropolitan's available houses' attributes, including heating information.

        Process
        -------
        * Converts a Metropolitan Statistical Area name into its constituent ZIP codes
        * For each ZIP code, searches Redfin with filters and collects listing results. ZIP codes are searched to ensure maximal data collection, as Redfin only returns (9 pages * 40 listings) 360 entries per search.
        * For each listing collected, creates a DataFrame of house attributes, such as location and heating amenities.

        Args:
            metro_name (str): a Metropolitan Statistical Area name
            filters_path (str): a filters path to search with

        Returns:
            pl.DataFrame: DataFrame of collected listing information
        """
        if filters_path is not None:
            self.logger.info(
                f"Filter path was supplied, overwriting filter string {helper.ASCIIColors.YELLOW}{self.filters_path}{helper.ASCIIColors.RESET} with {helper.ASCIIColors.YELLOW}{filters_path}{helper.ASCIIColors.RESET}"
            )
            self.set_filters_path(filters_path)
            self.logger.debug(f"Metro is using filter string: {self.filters_path}")
        zip_codes = helper.metro_name_to_zip_code_list(metro_name)

        if len(zip_codes) == 0:
            self.logger.debug("no zip codes returned from metro name conversion")
            return pl.DataFrame(schema=self.LISTING_SCHEMA)

        zip_code_search_page_csvs_df = self._zips_to_search_page_csvs(zip_codes)

        if zip_code_search_page_csvs_df is None:
            self.logger.info("Supplied zip codes do not have listings. Relax filters?")
            return pl.DataFrame(schema=self.LISTING_SCHEMA)

        # house attribs check
        return self.listing_attributes_from_search_page_csv(
            zip_code_search_page_csvs_df
        )

    def listing_attributes_from_search_page_csv(
        self, search_page_csvs: pl.DataFrame
    ) -> pl.DataFrame:
        """Given a dataframe with a column of "URL (SEE ht...)", this will look up the listings page and scrape specific house attributes.

        Args:
            search_page_csvs (pl.DataFrame): search page CSV DataFrame

        Returns:
            pl.DataFrame: the DataFrame. Is empty if no house has heating data
        """
        url_col_name = "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
        self.logger.info("Starting lookups on listing URLS")
        # might make two function argument to pass in address, so that logs can happen inside the amenities scrap func
        # if cant make two function arg, can build two cols into list and pass the list using
        return (
            search_page_csvs.with_columns(
                (pl.concat_list([pl.col("ADDRESS"), pl.col(url_col_name)]))
                .map_elements(listing_scraper.heating_amenities_scraper)
                .cast(pl.List(pl.Utf8))
                .alias("HEATING AMENITIES")
            )
            .filter(pl.col("HEATING AMENITIES").list.len().gt(pl.lit(0)))
            .drop(url_col_name)
        )
