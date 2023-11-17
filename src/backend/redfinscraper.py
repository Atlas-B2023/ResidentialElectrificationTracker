import copy
import io
import itertools
import os
import random
import re
import time
import json
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import polars as pl
import redfin
import requests
import undetected_chromedriver as uc
from backend import (
    ASCIIColors,
    get_redfin_url_path,
    logger,
    metro_name_to_zip_code_list,
    redfin_session,
)
from bs4 import BeautifulSoup as btfs
from bs4 import element
from fake_useragent import UserAgent

# def suppress_exception_in_del(uc):
#     old_del = uc.Chrome.__del__

#     def new_del(self) -> None:
#         try:
#             old_del(self)
#         except:
#             pass

#     setattr(uc.Chrome, "__del__", new_del)


# suppress_exception_in_del(uc)

exclude_terms = [
    # listings say things like "Electric: 200+ amps"
    re.compile(r"^electric", re.I),
    re.compile(r"no\b.*electric", re.I),
    re.compile(r"no\b.*gas", re.I),
    # hot water related things. the water has to get heated somehow... This might get rid of some strings that have all utilities listed together.
    # still leaven tho because a lot list how their hot water is heated
    re.compile(r"water", re.I),
    re.compile(r"utilities:", re.I),
    # if you want to disable collection of cooling un-comment
    # re.compile(r"cool", re.I),
]

heating_related_property_details_headers = [
    re.compile(r"heat", re.I),
    re.compile(r"property", re.I),
    # ies and y
    re.compile(r"utilit", re.I),
]

heating_related_patterns = [
    re.compile(r"electric", re.I),
    re.compile(r"resist(?:ive|ance)", re.I),
    re.compile(r"diesel|oil", re.I),
    re.compile(r"propane", re.I),
    re.compile(r"gas", re.I),
    re.compile(r"solar", re.I),
    # Only match wood if it comes after fuel, or before stove or burner
    re.compile(r"fuel\b.*\bwood|wood(en)* stove|wood(en)* burner", re.I),
    re.compile(r"pellet", re.I),
    re.compile(r"boiler", re.I),
    re.compile(r"baseboard", re.I),
    re.compile(r"furnace", re.I),
    re.compile(r"heat\spump", re.I),
    re.compile(r"mini[\s-]split", re.I),
    re.compile(r"radiator", re.I),
    re.compile(r"radiant", re.I),
]

regex_category_patterns = {
    "Electricity": re.compile(r"electric", re.I),
    "Natural Gas": re.compile(r"gas", re.I),
    "Propane": re.compile(r"propane", re.I),
    "Diesel/Heating Oil": re.compile(r"diesel|oil", re.I),
    "Wood/Pellet": re.compile(r"wood|pellet", re.I),
    "Solar Heating": re.compile(r"solar", re.I),
    # ask zack about the central electric match being a heat pump
    # central.*electric  #(?!.*mini-split)
    "Heat Pump": re.compile(r"heat pump|mini[\s-]split", re.I),
    "Baseboard": re.compile(r"baseboard", re.I),
    "Furnace": re.compile(r"furnace", re.I),
    "Boiler": re.compile(r"boiler", re.I),
    "Radiator": re.compile(r"radiator", re.I),
    "Radiant Floor": re.compile(r"radiant", re.I),
}

output_dir_path = f"{Path(os.path.dirname(__file__)).parent.parent}{os.sep}output"


class ContextedDriver:
    def __enter__(self):
        ua = UserAgent(min_percentage=10.0)
        user_agent = ua.random

        self.options = uc.ChromeOptions()
        self.options.add_argument("--auto-open-devtools-for-tabs")
        self.options.add_argument(f"--user-agent={user_agent}")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--blink-settings=imagesEnabled=false")

        # TODO get this automatically. only support chrome tho
        # C:\Users\*\AppData\Local\Programs\Opera GX\opera.exe
        # C:\Program Files\Google\Chrome\Application\chrome.exe
        self.driver = uc.Chrome(
            # this has to be searched
            browser_executable_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            # this is relative
            executable_path="D:\\Code\\Python\\atlas_project\\ResidentialElectrificationTracker\\chrome_driver\\chromedriver-win64\\chromedriver.exe",
            options=self.options,
            headless=True,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()
        time.sleep(0.1)


class RedfinListingScraper:
    """Scraper for Redfin listing pages."""

    def __init__(self, listing_url: str | None = None):
        # probably going to trip someone up if they make another function. just trying to allow you to set on object creation or not set
        self.listing_url = listing_url
        self.soup = None
        if listing_url is not None:
            self.soup = self.make_soup(listing_url)
            self.listing_url = listing_url
        self.column_dict = {key: False for key in regex_category_patterns.keys()}
        self.session = requests.Session()

    def req_wrapper(self, url: str) -> requests.Response:
        """A `request.get()` wrapper for connection pooling to Redfin's CSV download page

        Args:
            url (str): the url

        Returns:
            requests.Response: the `Response` object
        """
        time.sleep(random.uniform(1.1, 4))
        redfin_session.headers = self.get_gen_headers(url)  # type: ignore
        req = redfin_session.get(url)
        logger.info(f"{req.cookies.keys() =}")
        return req

    def get_gen_headers(self, url) -> dict[str, str]:
        """Generate headers for a connection to the Redfin CSV download page

        Returns:
            dict[str, str]: headers
        """
        referer_num = random.choice([1, 2, 3])
        referer = url
        if referer_num == 1:
            referer = "https://www.google.com/"
        elif referer_num == 2:
            referer = "https://ogs.google.com/"

        ua = UserAgent(min_percentage=0.1)
        return {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            # you can make this more complicated, like coming from a listing page, or something like https://www.redfin.com/city/14825/MI/New-Buffalo
            "Referer": referer,
        }

    def make_soup(self, listing_url: str) -> btfs:
        """Create `BeautifulSoup` object. Use output to set object's `self.soup`.

        Args:
            listing_url (str): listing URL

        Returns:
            btfs: the soup
        """
        html = None
        with ContextedDriver() as cd:
            cd.driver.get(listing_url)
            time.sleep(1.5)
            html = cd.driver.page_source

        logger.debug(f"Making soup for {listing_url = }")

        soup = btfs(html, "html.parser")
        if soup is None:
            logger.error(f"Soup is `None` for {listing_url = }")
        return soup

    def heating_terms_list_to_categorized_df_dict(
        self, my_list: list[str]
    ) -> dict[str, bool]:
        """Takes in a list of cleaned heating terms and produces a dict of categories of heater types

        Args:
            my_list (list[str]): clean heating terms list

        Returns:
            dict[str, bool]: the dict from column to the value mapping
        """
        master_dict = copy.deepcopy(self.column_dict)
        if len(my_list) == 0:
            return master_dict
        logger.debug(f"master dict {master_dict = }")
        for input_string in my_list:
            logger.debug(f"{input_string = }")
            result = {}
            for key, pattern in regex_category_patterns.items():
                if bool(re.search(pattern, input_string)):
                    result[key] = True
                    logger.debug(f"Pattern matched on {key, pattern = }")
                logger.debug(f"Pattern did not match on {key, pattern = }")
            for key in result.keys():
                master_dict[key] = result[key] | master_dict[key]

        # You'll have to df.unnest this for use in a dataframe
        logger.debug(my_list)
        logger.debug(master_dict)
        return master_dict

    def extract_heating_terms_from_list(self, terms_list: list[str]) -> list[str]:
        """Extract a list of terms related to heating from the specified list.

        Note:
            Uses an include and exclude list, heating_related_patterns, exclude_terms, respectively.

        Args:
            terms_list (list[str]): list of terms

        Returns:
            list[str]: terms dealing with heating
        """

        # here we just care that anything matches, not categorizing yet
        heating_terms_list = []
        # have a and not any(excluded_terms)?

        for string in terms_list:
            if any(
                regex.findall(string) for regex in heating_related_patterns
            ) and not any(regex.findall(string) for regex in exclude_terms):
                heating_terms_list.append(string)

        return heating_terms_list

    def get_property_details(self) -> element.PageElement | None:
        """Get the `propertyDetails-collapsible` div. This contains property details.

        Returns:
            element.PageElement | None: the div
        """
        if self.soup is None:
            logger.error("Soup is None for this listing.")
            # not sure how to handle, should not happen though
        prop_details_container = self.soup.find("div", id="propertyDetails-collapsible")  # type: ignore
        if prop_details_container is None:
            # logging handled in caller since we dont know the address in this scope
            if self.soup is not None:
                robot = self.soup.findAll(text=re.compile("you're not a robot"))
                if len(robot) > 0:
                    logger.warning("Web scraping likely detected!!")
                else:
                    logger.warning("Soup is not none, check contents!!")
                    output_path = Path(__file__).absolute().parent.parent.parent / Path(
                        f"output/{time.time()}.log"
                    )
                    logger.info(f"{self.listing_url}\n{self.soup.prettify()[:10000]}")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(f"{self.listing_url}\n")
                        f.write(f"{self.soup.prettify(encoding="utf-8")}")
            return None
        prop_details = prop_details_container.find("div", class_="amenities-container")  # type: ignore
        if prop_details is None:
            logger.warning(
                "Details not under details pane. This should not happen unless local laws require signing into Redfin to view data."
            )
            return None
        # returns <div class="amenities-container">
        return prop_details

    def get_amenity_super_groups(
        self, amenities_container_elements: element.PageElement
    ) -> list[str | element.PageElement | Any]:
        """Take in the `amenities-container` and return `super-group-content`s and their corresponding titles batched together.

        Args:
            amenities_container_elements (element.PageElement): The `amenities-container`

        Returns:
            list[str | element.PageElement | Any]: title, contents of `super-group-content` divs
        """
        title_content_pairs = itertools.batched(
            amenities_container_elements.children,  # type: ignore
            2,
        )
        return [[title.text, content] for title, content in title_content_pairs]

    def get_probable_heating_amenity_groups(
        self, super_group: element.PageElement
    ) -> list[Any]:
        """Take `super-group-content` div and return `amenity-group`s that likely have heating info.

        Note:
            Uses `self.heating_related_property_details_headers` for matching names
        Args:
            super_group (element.PageElement): a `super-group-content` div

        Returns:
            list[Any]: list of `amenity-group` divs
        """
        list_of_amenity_groups = []
        for amenity_group in super_group.children:  # type: ignore
            # check if the amenity group is related to heating
            amenity_group_name = (
                amenity_group.find("ul")
                .find("div", class_="propertyDetailsHeader")
                .text
            )
            if any(
                [
                    regex.findall(amenity_group_name)
                    for regex in heating_related_property_details_headers
                ]
            ):
                list_of_amenity_groups.append(amenity_group)
        return list_of_amenity_groups

    def get_heating_terms_from_amenity_group(
        self, amenity_group: element.PageElement
    ) -> list[str]:
        """Get a list of heating terms from the specified `amenity-group` div.

        Args:
            amenity_group (element.PageElement): the specified `amenity-group` div

        Returns:
            list[str]: list of heating terms
        """
        terms = [
            term_span.text
            for term_span in amenity_group.find_all("span", class_="entryItemContent")  # type: ignore
        ]
        return self.extract_heating_terms_from_list(terms)

    def get_heating_terms_df_dict_from_listing(
        self, addr_and_listing_url: list[str]
    ) -> dict[str, bool]:
        """Find heating terms under the property details section of a Redfin listing.

        Args:
            addr_and_listing_url (str | None, optional): The listing url. Defaults to None.

        Returns:
            list[str]: list of heating terms
        """
        addr, self.listing_url = addr_and_listing_url
        # this is actually kinda stupid
        self.soup = self.make_soup(self.listing_url)
        heating_terms = []
        details = self.get_property_details()
        if details is not None:
            logger.info(f"Getting property details for {addr}.")
            amenity_super_groups = self.get_amenity_super_groups(details)
            if amenity_super_groups is not None:
                for title, amenity_group in amenity_super_groups:  # type: ignore
                    logger.debug(f"Getting terms from the super group: {title}")
                    heating_amenity_groups = self.get_probable_heating_amenity_groups(
                        amenity_group  # type: ignore
                    )
                    for heating_amenity_group in heating_amenity_groups:
                        heating_terms.extend(
                            self.get_heating_terms_from_amenity_group(
                                heating_amenity_group
                            )
                        )
            else:
                logger.debug(
                    f"No amenity super groups in valid details section. Investigate {self.listing_url}"
                )
                return self.column_dict
        else:
            logger.warning(f"Could not find property details for {addr}.")
            # logger.info(f"{self.soup =}")
            return self.column_dict
        cat_dict = self.heating_terms_list_to_categorized_df_dict(heating_terms)
        # make this debug later
        logger.info(f"Housing info: {cat_dict}")
        return cat_dict


class RedfinSearcher:
    """
    Scrape Redfin and make use of their stingray API for retrieving housing information.

    Examples:
        >>> rfs = RedfinSearcher()
        >>> filters = rfs.generate_filters_path(...)
        >>> rfs.set_filters_path(filters)
        shape(3,3)
    """

    class PropertyType(StrEnum):
        """Properties of the `property-type` filter."""

        HOUSE = "house"
        CONDO = "condo"
        TOWNHOUSE = "townhouse"
        LAND = "land"
        OTHER = "other"
        MANUFACTURED = "manufactured"
        COOP = "co-op"
        MULTIFAMILY = "multifamily"

    class Status(StrEnum):
        """Properties of the `status` filter.

        Note:
            Do not use in conjunction with `Include`. Use of the `status` filter on Redfin implies the house is for sale.
            By default, Redfin searches for \"active\" and \"commingsoon\". This behavior is not replicated
        """

        ACTIVE = "active"
        COMINGSOON = "comingsoon"
        CONTINGENT = "contingent"
        PENDING = "pending"

    class Include(StrEnum):
        """Properties of the `include` filter."""

        LAST_1_WEEK = "sold-1wk"
        LAST_1_MONTH = "sold-1mo"
        LAST_3_MONTHS = "sold-3mo"
        LAST_6_MONTHS = "sold-6mo"
        LAST_1_YEAR = "sold-1yr"
        LAST_2_YEAR = "sold-2yr"
        LAST_3_YEAR = "sold-3yr"
        LAST_5_YEAR = "sold-5yr"

    class Stories(StrEnum):
        """Properties of the `min-stories` filter."""

        ONE = "1"
        TWO = "2"
        THREE = "3"
        FOUR = "4"
        FIVE = "5"
        TEN = "10"
        FIFTEEN = "15"
        TWENTY = "20"

    class Sqft(StrEnum):
        """Properties of the `min-sqft` and `max-sqft` filter."""

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
        """Properties of the `sort` filter.

        Note:
            Filters `NEWEST` and `MOST_RECENTLY_SOLD` are mutually exclusive.
        """

        # for sale only
        NEWEST = "lo-days"
        # sold only
        MOST_RECENTLY_SOLD = "hi-sale-date"
        # both
        LOW__TO_HIGH_PRICE = "lo-price"
        HIGH_TO_LOW_PRICE = "hi-price"
        SQFT = "hi-sqft"
        LOT_SIZE = "hi-lot-sqf"
        PRICE_PER_SQFT = "lo-dollarsqft"

    def __init__(self, filters_path: str | None = None) -> None:
        self.REDFIN_BASE_URL = "https://www.redfin.com"
        if filters_path is None:
            self.filters_path = self.generate_filters_path(
                sort=self.Sort.MOST_RECENTLY_SOLD,
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
            "ADDRESS"
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
            "ZIP OR POSTAL CODE": pl.UInt32,
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
            "ZIP OR POSTAL CODE": pl.UInt32,
            "PRICE": pl.UInt32,
            "SQUARE FEET": pl.UInt32,
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)": str,
            "LATITUDE": pl.Float32,
            "LONGITUDE": pl.Float32,
        }
        self.session = requests.Session()

    @staticmethod
    def generate_filters_path(**kwargs) -> str:
        """Generate the path for the specified filters.

        Note:
            When using `include`, you cannot use: `status` TODO

            When searching by f, you cannot use: TODO

        Available filters:
            * `include`
            * `property-type`
            * `min-beds`
            * `max-beds`
            * `min-baths`
            * `max-baths`
            * `min-year-built`
            * `max-year-built`
            * `status`
            * `min-price`
            * `max-price`
            * `sort`
            * `exclude-age-restricted`
            * `is-green`
            * `fireplace`
            * `min-stories`
            * `min-sqft`

        Examples:
            For generating a filter string that has a filter with 1 value:

            >>> generate_filters_path(min-sqft=Sqft.THOU, property_type=PropertyType.HOUSE)
            "/filter/min-sqft=1k,property-type=house"

            For generating a filter string that has a filter with multiple values:

            >>> generate_filters_path(min-sqft=Sqft.THOU, property_type=[PropertyType.HOUSE, PropertyType.TOWNHOUSE])
            "/filter/min-sqft=1k,property-type=house+townhouse"

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

        return f"/filter/{",".join(selected_filters)}"

    def set_filters_path(self, filters_path: str) -> None:
        """Set the search filters for all searches made with this RedfinSearcher object.

        Args:
            filters_path (str): the URL path to search with
        """
        logger.debug(f"Setting filters to: {filters_path}")
        self.filters_path = filters_path

    def generate_area_path(self, zip_code_or_city_and_state_or_address: str) -> str:
        """Generate the path for the specified location. Redfin uses proprietary numbers to identify cities. This makes a call to their
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
        path_url = f"{get_redfin_url_path(zip_code_or_city_and_state_or_address)}"
        return path_url

    def req_wrapper(self, url: str) -> requests.Response:
        # redfin refusing to connect on listing connections. can reproduce on browser by blocking all cookies
        #     self.session = requests.Session()
        # redfin gets about 38 visits a second per month
        time.sleep(random.uniform(0.5, 0.9))
        redfin_session.headers = self.get_gen_headers()  # type: ignore
        req = redfin_session.get(url)
        return req

    def get_gen_headers(self) -> dict[str, str]:
        ua = UserAgent()
        return {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "Sec-Fetch-Dest": "iframe",  # document
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",  # none
            "Sec-GPC": "1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
        }

    def df_from_search_page_csv(self, url: str) -> pl.DataFrame | None:
        """Return a DataFrame of the contents scraped from the \"Download all\" button on the specified search page URL.

        Note:
            The schema of this DataFrame is listed in `RedfinSearcher.CSV_SCHEMA`.

        Raises:
            TypeError: if the csv cant find the download link button and there are listings available

        Args:
            url (str): the URL of the search page

        Returns:
            pl.DataFrame | None: the DataFrame. Is None if there are no listings for the given filters. Is None if the CSV download link is not available
        """
        html = None
        with ContextedDriver() as cd:
            cd.driver.get(url)
            time.sleep(1)
            html = cd.driver.page_source

        soup = btfs(html, "html.parser")
        download_button_id = "download-and-save"
        download_link_tag = soup.find("a", id=download_button_id)

        if download_link_tag is None:
            # should be handled in caller
            # randomly gives this error. investigate, if truly just random, retry in one second. 11/2 think i fixed it
            if soup.find("body", class_="route-SearchPage") is not None:
                # valid zip code but no results show.
                logger.debug(
                    f"No heating information with the specified filters for {url}"
                )
                return None
            elif soup.find("body", class_="route-NotFoundPage") is not None:
                # given when you search a fake zip code
                logger.info(f"Zip code does not exist {url}")
                return None
            else:
                raise TypeError(
                    f"Could not find CSV download. Check if the html downloaded is correct, or if the download button id has changed. Info: {url = }, {len(html) = }"
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

        csv_download = self.req_wrapper(f"{self.REDFIN_BASE_URL}{download_link}")
        try:
            # can be empty
            csv_download.raise_for_status()
            csv = csv_download.text
            df = (
                pl.read_csv(
                    io.StringIO(csv),
                    dtypes=self.CSV_SCHEMA,
                )
                .filter(pl.col("PROPERTY TYPE").eq("Single Family Residential"))
                .select(
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
            )
        except HTTPError as e:
            print(e)
            logger.error(
                f"Download for {url} returned a {csv_download.status_code} status code. Most likely download has been moved."
            )
            return None
        if df.height == 0:
            logger.debug(
                "Downloaded csv was empty. Can happen if MLS does not allow downloads"
            )
            return None
        return df

    def zips_to_search_page_csvs(self, zip_codes: list[int]) -> pl.DataFrame | None:
        """Return a DataFrame produced by concatenating all of the specified ZIP codes' search page CSVs.

        Args:
            zip_codes (list[int]): list of ZIP codes to search

        Returns:
            pl.DataFrame | None: the concatenated DataFrame. Is empty if there are no listings for the given filters. Is None if the CSV download link is not available
        """
        formatted_zip_codes = [f"{zip_code:0{5}}" for zip_code in zip_codes]
        list_of_csv_dfs = []

        for zip_code in formatted_zip_codes:
            search_page_url = f"{self.REDFIN_BASE_URL}{self.generate_area_path(zip_code)}{self.filters_path}"
            logger.debug(f"searching zip code with {search_page_url = }")
            try:
                # this is the only place where this error should pop up. if a zip is invalid,
                # return none and handle in caller. an example is the zip 56998, which is just a
                # USPS distribution center in D.C
                # should df_from_search_page be returning none
                redfin_csv_df = self.df_from_search_page_csv(search_page_url)
            except requests.HTTPError as e:
                #! this also gave random error
                logger.warning(
                    f"{search_page_url = }, {zip_code = } gave an invalid zip code (possible its something else) error.\n{e}"
                )
                # return None
                continue

            if redfin_csv_df is None:
                logger.info(
                    f"The download link for {zip_code}'s search page is not available."
                )
                continue

            logger.info(f"Found download link for {zip_code}'s search page.")
            list_of_csv_dfs.append(redfin_csv_df)
        if len(list_of_csv_dfs) == 0:
            return None
        else:
            return pl.concat(list_of_csv_dfs)

    def listing_attributes_from_search_page_csv(
        self, search_page_csvs: pl.DataFrame
    ) -> pl.DataFrame:
        """Get house attributes from URLS supplied in the specified DataFrame, given that it has a column with the name "URL (SEE ht...)".

        Args:
            search_page_csvs (pl.DataFrame): search page CSV DataFrame

        Returns:
            pl.DataFrame: the DataFrame. Is empty if no house has heating data
        """
        url_col_name = "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
        logger.info("Starting lookups on listing URLS")
        # can have more than 1 zip in csv. save file, then append each listing?
        logger.info(
            f"Unique ZIP codes: {search_page_csvs["ZIP OR POSTAL CODE"].n_unique()}"
        )
        logger.info(f"Estimated completion time: {search_page_csvs.height * 4} seconds")
        rls = RedfinListingScraper()

        return (
            search_page_csvs.with_columns(
                pl.concat_list([pl.col("ADDRESS"), pl.col(url_col_name)])
                .map_elements(rls.get_heating_terms_df_dict_from_listing)
                .alias("nest")
            )
            .drop(url_col_name)
            .unnest("nest")
        )

    def load_house_attributes_from_metro_to_file(
        self, metro_name: str, filters_path: str | None = None
    ) -> None:
        """Create a DataFrame of a metropolitan's available houses' attributes, including heating information.

        Note:
            The process is as follows:
            * Convert a Metropolitan Statistical Area name into its constituent ZIP codes
            * For each ZIP code, search Redfin with filters and collect listing results. (ZIP codes are searched to ensure maximal data collection, as Redfin only returns (9 pages * 40 listings) 360 entries per search.)
            * For each listing collected, creates a DataFrame of house attributes, such as location and heating amenities.

        Args:
            metro_name (str): a Metropolitan Statistical Area name
            filters_path (str): a filters path to search with

        Returns:
            pl.DataFrame: DataFrame of collected listing information
        """
        if filters_path is not None:
            logger.info(
                f"Filter path was supplied, overwriting filter string {ASCIIColors.YELLOW}{self.filters_path}{ASCIIColors.RESET} with {ASCIIColors.YELLOW}{filters_path}{ASCIIColors.RESET}"
            )
            self.set_filters_path(filters_path)
            logger.debug(f"Metro is using filter string: {self.filters_path}")
        zip_codes = metro_name_to_zip_code_list(metro_name)

        if len(zip_codes) == 0:
            logger.debug("no zip codes returned from metro name conversion")
            return
            # return pl.DataFrame(schema=self.LISTING_SCHEMA)

        zip_code_search_page_csvs_df = self.zips_to_search_page_csvs(zip_codes)

        if zip_code_search_page_csvs_df is None:
            logger.info("Supplied zip codes do not have listings. Relax filters?")
            return
            # return pl.DataFrame(schema=self.LISTING_SCHEMA)

        # house attribs check

        full_df = self.listing_attributes_from_search_page_csv(
            zip_code_search_page_csvs_df
        )

        output_metro_dir_path = Path(f"{output_dir_path}{os.sep}{metro_name}{os.sep}")

        try:
            os.mkdir(output_metro_dir_path)
        except FileExistsError:  # exists
            pass

        list_of_dfs_by_zip = full_df.partition_by("ZIP OR POSTAL CODE")
        for df_by_zip in list_of_dfs_by_zip:
            # make file name the zip code
            zip = df_by_zip.select("ZIP OR POSTAL CODE").item()
            df_by_zip.write_csv(f"{output_metro_dir_path}{zip}")


class NewScraper:
    """Scrape redfin using their stingray api. Use this class for getting and the iterating over ZIP code level data, creating an object for each new zip code."""

    class HouseType(StrEnum):
        HOUSE = "1"
        CONDO = "2"
        TOWNHOUSE = "3"
        MULTI_FAMILY = "4"
        LAND = "5"
        OTHER = "6"

    class SortOrder(StrEnum):
        RECOMMENDED = "redfin-recommended-asc"
        NEWEST = "days-on-redfin-asc"
        MOST_RECENTLY_SOLD = "last-sale-date-desc"
        LOW_HI = "price-asc"
        HI_LOW = "price-desc"
        SQFT = "square-footage-desc"
        LOT_SIZE = "lot-sq-ft-desc"
        SQFT_PRICE = "dollars-per-sq-ft-asc"

    class SoldWithinDays(StrEnum):
        ONE_WEEK = "7"
        ONE_MONTH = "30"
        THREE_MONTHS = "90"
        SIX_MONTHS = "180"
        ONE_YEARS = "365"
        TWO_YEARS = "730"
        THREE_YEARS = "1095"
        FIVE_YEARS = "1825"

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
        """Properties of the `min-sqft` and `max-sqft` filter."""

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

    def __init__(self) -> None:
        self.rf = redfin.Redfin()
        self.DESIRED_CSV_SCHEMA = {
            "ADDRESS": str,
            "CITY": str,
            "PROPERTY TYPE": str,
            "STATE OR PROVINCE": str,
            "YEAR BUILT": pl.UInt16,
            "ZIP OR POSTAL CODE": pl.UInt32,
            "PRICE": pl.UInt32,
            "SQUARE FEET": pl.UInt32,
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)": str,
            "LATITUDE": pl.Float32,
            "LONGITUDE": pl.Float32,
        }
        self.search_params = None

    def meta_request_download(self, url, kwargs) -> str:
        response = requests.get(
            self.rf.base + url, params=kwargs, headers=self.rf.user_agent_header
        )
        response.raise_for_status()
        return response.text

    def get_region_info_from_zipcode(self, zip_code: str) -> Any:
        return self.rf.meta_request(
            "api/region", {"region_id": zip_code, "region_type": 2, "tz": True, "v": 8}
        )

    def get_gis_csv(self, params) -> str:
        return self.meta_request_download("api/gis-csv", params)

    def set_search_params(
        self,
        zip: str,
        min_year_built: str,
        max_year_built: str,
        min_stories: Stories,
        sort_order: SortOrder,
        home_types: list[HouseType],
        sold: SoldWithinDays | None = SoldWithinDays.FIVE_YEARS,
    ) -> None:
        """Set the parameters for searching by zip code

        Args:
            zip (str): _description_
            min_year_built (str): _description_
            max_year_built (str): _description_
            min_stories (Stories): _description_
            sort_order (SortOrder): _description_
            home_types (list[HouseType]): _description_
            sold (SoldWithinDays | None, optional): _description_. Defaults to SoldWithinDays.FIVE_YEARS.

        Returns:
            _type_: _description_
        """
        try:
            region_info = self.get_region_info_from_zipcode(zip)
        except json.JSONDecodeError as e:
            logger.warning("Error decoding region info.")
            return None
        except HTTPError:
            logger.warning("Error retrieving region info.")
            return None
        
        if sold:
            if sort_order is self.SortOrder.NEWEST:
                logger.warning("Wrong sort order for sale type")
                return None
        else:
            if sort_order is self.SortOrder.MOST_RECENTLY_SOLD:
                logger.warning("Wrong sort order for sale type")
                return None

        try:
            market = region_info["payload"]["rootDefaults"]["market"]
            region_id = region_info["payload"]["rootDefaults"]["region_id"]
            status = str(region_info["payload"]["rootDefaults"]["status"])
        except KeyError:
            logger.warn("Market, region, or status could not be identified ")
            return None

        self.search_params = {
            "al": 1,
            "has_deal": "false",
            "has_dishwasher": "false",
            "has_laundry_facility": "false",
            "has_laundry_hookups": "false",
            "has_parking": "false",
            "has_pool": "false",
            "max_year_built": max_year_built,
            "min_stories": min_stories.value,
            "min_year_built": min_year_built,
            "has_short_term_lease": "false",
            "include_pending_homes": "false",  # probably an "include" option
            "isRentals": "false",
            "is_furnished": "false",
            "is_income_restricted": "false",
            "is_senior_living": "false",
            "market": market,
            "num_homes": 350,
            "ord": sort_order,
            "page_number": "1",
            "pool": "false",
            "region_id": region_id,
            "region_type": 2,
            "status": status,
            "travel_with_traffic": "false",
            "travel_within_region": "false",
            "uipt": ",".join(val for val in home_types),
            "utilities_included": "false",
            "v": "8",
        }
        if sold is not None:
            self.search_params["sold_within_days"] = sold.value
        else:
            self.search_params["sf"] = 1, 2, 3, 5, 6, 7

    def get_super_groups_from_address(self, addr: str) -> Any | None:
        response = self.rf.search(addr)
        try:
            url = response["payload"]["exactMatch"]["url"]
            print(url)
        except KeyError:
            try:
                url = response["payload"]["sections"][0]["rows"][0]["url"]
            except KeyError:
                print("Address not found")
                return None
        initial_info = self.rf.initial_info(url)
        property_id = initial_info["payload"]["propertyId"]
        mls_data = self.rf.below_the_fold(property_id)
        return mls_data["payload"]["amenitiesInfo"]["superGroups"]

    def get_gis_csv_from_zip_with_filters(
        self,
    ) -> pl.DataFrame | None:
        """Main function.

        Args:
            zip (str): ZIP code
            min_year_built (str): Min year built to filter
            max_year_built (str): Max year built to filter
            min_stories (Stories): Min stories to filter
            sort_order (SortOrder): How to filter results. Maximum of 350 results can be retrieved. Look into `page=1`
            home_types (list[HouseType]): Home type
            sold (SoldWithinDays | None, optional): If searching for sold homes, pass this argument. Defaults to SoldWithinDays.FIVE_YEARS.

        TODO:
            handle empty csv page. can try with normal filters and rural town.
            handle None for sold if modifications are to be added to how sales are to be done?
        Returns:
            pl.DataFrame | None: DataFrame of listings for the given ZIP code and filters
        """
        # TODO, handle empty csv page. can try with normal filters and rural town

        # TODO, the stuff for when searching by for sale. on back burner cause not useful rn
   
        # region_info = self.get_region_info_from_zipcode(zip)
        
        # if sold:
        #     if sort_order is self.SortOrder.NEWEST:
        #         logger.warning("wrong sort order for sale type")
        #         return
        # else:
        #     if sort_order is self.SortOrder.MOST_RECENTLY_SOLD:
        #         logger.warning("wrong sort order for sale type")
        #         return
        # market = region_info["payload"]["rootDefaults"]["market"]
        # region_id = region_info["payload"]["rootDefaults"]["region_id"]
        # status = str(region_info["payload"]["rootDefaults"]["status"])
        # # sold:
        # params = {
        #     "al": 1,
        #     "has_deal": "false",
        #     "has_dishwasher": "false",
        #     "has_laundry_facility": "false",
        #     "has_laundry_hookups": "false",
        #     "has_parking": "false",
        #     "has_pool": "false",
        #     "max_year_built": max_year_built,
        #     "min_stories": min_stories.value,
        #     "min_year_built": min_year_built,
        #     "has_short_term_lease": "false",
        #     "include_pending_homes": "false",  # probably an "include" option
        #     "isRentals": "false",
        #     "is_furnished": "false",
        #     "is_income_restricted": "false",
        #     "is_senior_living": "false",
        #     "market": market,
        #     "num_homes": 350,
        #     "ord": sort_order,
        #     "page_number": "1",
        #     "pool": "false",
        #     "region_id": region_id,
        #     "region_type": 2,
        #     "status": status,
        #     "travel_with_traffic": "false",
        #     "travel_within_region": "false",
        #     "uipt": ",".join(val for val in home_types),
        #     "utilities_included": "false",
        #     "v": "8",
        # }
        # if sold is not None:
        #     params["sold_within_days"] = sold.value
        # else:
        #     params["sf"] = 1, 2, 3, 5, 6, 7
        # filter on what we want. currently were only accepting `HOUSE`
        if self.search_params is None:
            logger.warn(f"Search params were not set. {self.search_params = }.")
            return
        csv_text = self.get_gis_csv(self.search_params)
        try:
            df = (
                pl.read_csv(io.StringIO(csv_text), dtypes=self.DESIRED_CSV_SCHEMA)
                .filter(pl.col("PROPERTY TYPE").eq("Single Family Residential"))
                .select(
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
            )
            if df.height == 0:
                logger.debug("CSV was empty. This can happen if local MLS rules dont allow downloads.")
                return None
        except Exception as e:
            logger.warning(f"Could not read gis csv.\n{csv_text = }\n{e}")
            return None
        return df
    
    def get_gis_csv_for_zips_in_metro_with_filters(
        self,
        metro: str,
        min_year_built: str,
        max_year_built: str,
        min_stories: Stories,
        sort_order: SortOrder,
        home_types: list[HouseType],
        sold: SoldWithinDays | None = SoldWithinDays.FIVE_YEARS,
    ) -> pl.DataFrame | None:
        
        # zips = helper.metroname to zips
        # zips = formated zips
        # for zip in zips
        # ->
        zip_codes = metro_name_to_zip_code_list(metro)
        formatted_zip_codes = [f"{zip_code:0{5}}" for zip_code in zip_codes]
        list_of_csv_dfs = []
        for zip in formatted_zip_codes:
            time.sleep(random.uniform(.5, 1.6))
            self.set_search_params(zip, min_year_built, max_year_built, min_stories, sort_order, home_types, sold)
            temp = self.get_gis_csv_from_zip_with_filters()
            if temp is None:
                logger.info(f"Did not find any houses in {zip}.")
                continue
            logger.info(f"Found data for {temp.height} houses in {zip}.")
            list_of_csv_dfs.append(temp)

        return pl.concat(list_of_csv_dfs)
                
        #-> if not none all.append(zipcodecsv_search) else "nothing for for {zip = }"


    # get_csv_from_zip_with_filters(
    #     "01609",
    #     "2022",
    #     "2023",
    #     NewScraper.Stories.ONE,
    #     NewScraper.SortOrder.MOST_RECENTLY_SOLD,
    #     [NewScraper,HouseType.HOUSE],
    #     NewScraper.SoldWithinDays.FIVE_YEARS,
    # )
