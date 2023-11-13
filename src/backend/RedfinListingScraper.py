import copy
import itertools
import random
import re
import time
from datetime import datetime
from typing import Any

import requests
from backend import get_random_user_agent, logger, redfin_session
from bs4 import BeautifulSoup as btfs
from bs4 import element

# TODO these get finalized on monday with meeting with zack
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


class RedfinListingScraper:
    """Scraper for Redfin listing pages."""

    def __init__(self, listing_url: str | None = None):
        # probably going to trip someone up if they make another function. just trying to allow you to set on object creation or not set
        self.listing_url = listing_url
        self.soup = None
        if listing_url is not None:
            self.soup = self.make_soup(listing_url)
            self.listing_url = listing_url
        self.logger = logger
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
        self.logger.info(f"{req.cookies.keys() =}")
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

        return {
            "User-Agent": get_random_user_agent(),
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
        self.logger.debug(f"Making soup for {listing_url = }")
        req = self.req_wrapper(listing_url)
        req.raise_for_status()
        req.encoding = "utf-8"
        html = req.text
        soup = btfs(html, "html.parser")
        if soup is None:
            self.logger.error(
                f"Soup is `None` for {listing_url = }, {req.status_code = }"
            )
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
        self.logger.debug(f"master dict {master_dict = }")
        for input_string in my_list:
            self.logger.debug(f"{input_string = }")
            result = {}
            for key, pattern in regex_category_patterns.items():
                if bool(re.search(pattern, input_string)):
                    result[key] = True
                    self.logger.debug(f"Pattern matched on {key, pattern = }")
                self.logger.debug(f"Pattern did not match on {key, pattern = }")
            for key in result.keys():
                master_dict[key] = result[key] | master_dict[key]

        # You'll have to df.unnest this for use in a dataframe
        self.logger.debug(my_list)
        self.logger.debug(master_dict)
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
            self.logger.error("Soup is None for this listing.")
            # not sure how to handle, should not happen though
        prop_details_container = self.soup.find("div", id="propertyDetails-collapsible")  # type: ignore
        logger.info(f"{prop_details_container =}")
        if prop_details_container is None:
            # logging handled in caller since we dont know the address in this scope
            if self.soup is not None:
                robot = self.soup.findAll(text=re.compile("you're not a robot"))
                if len(robot) > 0:
                    self.logger.warning("Web scraping likely detected!!")
                else:
                    self.logger.warning("Soup is not none, check contents!!")
                # self.logger.debug(f"{self.soup = }")
            return None
        prop_details = prop_details_container.find("div", class_="amenities-container")  # type: ignore
        if prop_details is None:
            self.logger.warning(
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
            self.logger.info(f"Getting property details for {addr}.")
            amenity_super_groups = self.get_amenity_super_groups(details)
            if amenity_super_groups is not None:
                for title, amenity_group in amenity_super_groups:  # type: ignore
                    self.logger.debug(f"Getting terms from the super group: {title}")
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
                self.logger.debug(
                    f"No amenity super groups in valid details section. Investigate {self.listing_url}"
                )
                return self.column_dict
        else:
            self.logger.warning(f"Could not find property details for {addr}.")
            # self.logger.info(f"{self.soup =}")
            return self.column_dict

        return self.heating_terms_list_to_categorized_df_dict(heating_terms)
