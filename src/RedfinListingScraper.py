import re
import itertools
from typing import Any

import Helper as Helper
from bs4 import BeautifulSoup as btfs
from bs4 import element

exclude_terms = [
    # listings say things like "Electric: 200+ amps"
    re.compile(r"^electric", re.I),
    re.compile(r"(\bno).*electric", re.I),
    re.compile(r"water", re.I),
    re.compile(r"(utilities:)", re.I),
]
heating_related_property_details_headers = [
    re.compile(r"heat", re.I),
    re.compile(r"property", re.I),
    re.compile(r"utilit", re.I),
]
heating_related_patterns = [
    # * take forced out when doing the real project
    # re.compile(r"forced\sair", re.I),
    # re.compile(r"fuel", re.I),
    re.compile(r"furnace", re.I),
    re.compile(r"diesel", re.I),
    re.compile(r"\bfuel\b.*\bhot\swater", re.I),
    re.compile(r"solar\sheat", re.I),  # Active Solar Heating
    re.compile(r"resist(?:ive|ance)", re.I),
    re.compile(r"space\sheater", re.I),
    re.compile(r"hybrid\sheat", re.I),
    # have to check there there is no "no" in the line using (?<!\bno\s)
    re.compile(r"natural\sgas", re.I),
    re.compile(r"gas", re.I),
    re.compile(r"oil", re.I),
    re.compile(r"electric", re.I),
    re.compile(r"heat\spump", re.I),
    re.compile(r"propane", re.I),
    re.compile(r"baseboard", re.I),
    re.compile(r"mini[\s-]split", re.I),
    re.compile(r"pellet", re.I),
    # this tries to prevent matches like "Hardwood floors"
    re.compile(r"\bfuel\b.*\bwood", re.I),
    # re.compile(r"radiant", re.I),
]


class RedfinListingScraper:
    def __init__(self, listing_url: str | None = None):
        # probably going to trip someone up if they make another function. just trying to allow you to set on object creation or not set
        self.listing_url = listing_url
        self.soup = None
        if listing_url is not None:
            self.soup = self.make_soup(listing_url)
            self.listing_url = listing_url
        self.logger = Helper.logger

    def make_soup(self, listing_url: str) -> btfs:
        """Create `BeautifulSoup` object. Use output to set object's `self.soup`.

        Args:
            listing_url (str): listing URL

        Returns:
            btfs: the soup
        """
        self.logger.debug(f"Making soup for {listing_url = }")
        req = Helper.req_get_wrapper(listing_url)
        req.raise_for_status()
        req.encoding = "utf-8"
        html = req.text
        soup = btfs(html, "html.parser")
        if soup is None:
            self.logger.error(
                f"Soup is `None` for {listing_url = }, {req.status_code = }"
            )
        return soup

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
        prop_details_container = self.soup.find("div", id="propertyDetails-collapsible")

        if prop_details_container is None:
            # TODO handle this
            self.logger.info("Could not find property details")
            return None
        prop_details = prop_details_container.find("div", class_="amenities-container")  # type: ignore
        if prop_details is None:
            self.logger.info("Details not under Details pane. this shouldnt happen")
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
            _type_: title, contents of `super-group-content` divs
        """
        title_content_pairs = itertools.batched(
            amenities_container_elements.children, 2
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
        for amenity_group in super_group.children:
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
            for term_span in amenity_group.find_all("span", class_="entryItemContent")
        ]
        return self.extract_heating_terms_from_list(terms)

    def get_heating_terms_from_listing(
        self, addr_and_listing_url: list[str]
    ) -> list[str]:
        """Find heating terms under the property details section of a Redfin listing.

        Args:
            listing_url (str | None, optional): The listing url. Defaults to None.

        Returns:
            list[str]: list of heating terms
        """
        addr, self.listing_url = addr_and_listing_url
        # this is actually kinda stupid
        self.soup = self.make_soup(self.listing_url)
        all_items = []
        details = self.get_property_details()
        if details is not None:
            amenity_super_groups = self.get_amenity_super_groups(details)
            if amenity_super_groups is not None:
                for title, amenity_group in amenity_super_groups:  # type: ignore
                    self.logger.debug(f"Getting terms from the super group: {title}")
                    heating_amenity_groups = self.get_probable_heating_amenity_groups(
                        amenity_group  # type: ignore
                    )
                    for heating_amenity_group in heating_amenity_groups:
                        all_items.extend(
                            self.get_heating_terms_from_amenity_group(
                                heating_amenity_group
                            )
                        )
            else:
                self.logger.debug(
                    f"No amenity super groups in valid details section. Investigate {self.listing_url}"
                )
        else:
            self.logger.info(f"Could not find property details for {addr}.")

        if len(all_items) == 0:
            self.logger.info(f"{addr} did not have heating amenities.")
        else:
            self.logger.info(f"{addr} has heating amenities: {all_items}.")

        return all_items
