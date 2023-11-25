import copy
import io
import json
import os
import random
import re
import time
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse

import polars as pl
import redfin
import requests
from backend import (
    log,
    metro_name_to_zip_code_list,
)

# TODO add notice that this program may over estimate or under estimate fuels that are common across not heating system in houses, like electricity and NG
# How the searcher works:
# Uses super_group_heating_related_patterns to scan over supergroups and return the super groups that likely contain heating information
# for each of these super groups, it goes through and checks their amenity group headers.
# For each amenity group header, it uses amenity_group_include_patterns to filter.
# if there is no colon, it adds the result of filtering by appliance.
# if there is a colon, it filters with group names


# super group include
SUPER_GROUP_INCLUDE_PATTERNS = re.compile(r"heat|property|interior|utilit", re.I)

# amenity group include
AMENITY_GROUP_INCLUDE_PATTERNS = re.compile(r"heat|utilit|interior", re.I)

# before colon include
AMENITY_NAME_INCLUDE_PATTERNS = re.compile(r"heat", re.I)
# before colon exclude
AMENITY_NAME_EXCLUDE_PATTERNS = re.compile(
    r"heat.*updat|has heat|heat.*efficiency|heat.*certific", re.I
)

# dangling include and when the before colon word is utilities
APPLIANCE_HEATING_RELATED_PATTERNS = [
    re.compile(r"mini[\s-]split", re.I),
    re.compile(r"resist(?:ive|ance)", re.I),
    re.compile(r"\bwood(en)* stove|\bwood(en)* burner", re.I),
    re.compile(r"heat pump", re.I),
    re.compile(r"radiator", re.I),
    re.compile(r"furnace", re.I),
    re.compile(r"boiler", re.I),
    re.compile(r"radiant", re.I),
    re.compile(r"baseboard", re.I),
]

# ==
AFTER_COLON_FUEL_AND_APPLIANCE_INCLUDE_PATTERNS = [
    re.compile(r"electric", re.I),
    re.compile(r"diesel|oil", re.I),
    re.compile(r"propane", re.I),
    re.compile(r"gas", re.I),
    re.compile(r"solar", re.I),
    re.compile(r"wood", re.I),
    re.compile(r"pellet", re.I),
]

# after colon include
AFTER_COLON_FUEL_AND_APPLIANCE_INCLUDE_PATTERNS.extend(
    APPLIANCE_HEATING_RELATED_PATTERNS
)

# TODO figure where this goes
AFTER_COLON_EXCLUDE_PATTERNS = re.compile(r"no\b.*electric|no\b.*gas|water", re.I)

CATEGORY_PATTERNS = {
    "Electricity": re.compile(r"electric", re.I),
    "Natural Gas": re.compile(r"gas", re.I),
    "Propane": re.compile(r"propane", re.I),
    "Diesel/Heating Oil": re.compile(r"diesel|oil", re.I),
    "Wood/Pellet": re.compile(r"wood|pellet", re.I),
    "Solar Heating": re.compile(r"solar", re.I),
    "Heat Pump": re.compile(r"heat pump|mini[\s-]split", re.I),
    "Baseboard": re.compile(r"baseboard|resist", re.I),
    "Furnace": re.compile(r"furnace", re.I),
    "Boiler": re.compile(r"boiler", re.I),
    "Radiator": re.compile(r"radiator", re.I),
    "Radiant Floor": re.compile(r"radiant", re.I),
}

OUTPUT_DIR_PATH = f"{Path(os.path.dirname(__file__)).parent.parent}{os.sep}output"


class RedfinApi:
    """Scrape redfin using their stingray api. Use this class for getting and the iterating over ZIP code level data, creating an object for each new zip code."""

    class SoldStatus(StrEnum):
        FOR_SALE = "For Sale"
        SOLD = "Sold"

    class HouseType(StrEnum):
        HOUSE = "1"
        CONDO = "2"
        TOWNHOUSE = "3"
        MULTI_FAMILY = "4"
        LAND = "5"
        OTHER = "6"

    class Price(StrEnum):
        NONE = "None"
        FIFTY_THOU = "50000"
        SEVENTY_FIVE_THOU = "75000"
        ONE_HUN_THOU = "100000"
        ONE_HUN_25_THOU = "125000"
        ONE_HUN_5_THOU = "150000"
        ONE_HUN_75_THOU = "175000"
        TWO_HUN_THOU = "200000"
        TWO_HUN_25_THOU = "225000"
        TWO_HUN_5_THOU = "250000"
        TWO_HUN_75_THOU = "275000"
        THREE_HUN_THOU = "300000"
        THREE_HUN_25_THOU = "325000"
        THREE_HUN_5_THOU = "350000"
        THREE_HUN_75_THOU = "375000"
        FOUR_HUN_THOU = "400000"
        FOUR_HUN_25_THOU = "425000"
        FOUR_HUN_5_THOU = "450000"
        FOUR_HUN_75_THOU = "475000"
        FIVE_HUN_THOU = "500000"
        FIVE_HUN_5_THOU = "550000"
        SIX_HUN_THOU = "600000"
        SIX_HUN_5_THOU = "650000"
        SEVEN_HUN_THOU = "700000"
        SEVEN_HUN_5_THOU = "750000"
        EIGHT_HUN_THOU = "800000"
        EIGHT_HUN_5_THOU = "850000"
        NINE_HUN_THOU = "900000"
        NINE_HUN_5_THOU = "950000"
        ONE_MIL = "1000000"
        ONE_MIL_25_THOU = "1250000"
        ONE_MIL_5_THOU = "1500000"
        ONE_MIL_75_THOU = "1750000"
        TWO_MIL = "2000000"
        TWO_MIL_25_THOU = "2250000"
        TWO_MIL_5_THOU = "2500000"
        TWO_MIL_75_THOU = "2750000"
        THREE_MIL = "3000000"
        THREE_MIL_25_THOU = "3250000"
        THREE_MIL_5_THOU = "3500000"
        THREE_MIL_75_THOU = "3750000"
        FOUR_MIL = "4000000"
        FOUR_MIL_25_THOU = "4250000"
        FOUR_MIL_5_THOU = "4500000"
        FOUR_MIL_75_THOU = "4750000"
        FIVE_MIL = "5000000"
        SIX_MIL = "6000000"
        SEVEN_MIL = "7000000"
        EIGHT_MIL = "8000000"
        NINE_MIL = "9000000"
        TEN_MIL = "10000000"

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
        ONE_YEAR = "365"
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
        NONE = "None"
        SEVEN_FIFTY = "750"
        THOU = "1000"
        THOU_1 = "1100"
        THOU_2 = "1200"
        THOU_3 = "1300"
        THOU_4 = "1400"
        THOU_5 = "1500"
        THOU_6 = "1600"
        THOU_7 = "1700"
        THOU_8 = "1800"
        THOU_9 = "1900"
        TWO_THOU = "2000"
        TWO_THOU_250 = "2250"
        TWO_THOU_500 = "2500"
        TWO_THOU_750 = "2750"
        THREE_THOU = "3000"
        FOUR_THOU = "4000"
        FIVE_THOU = "5000"
        SEVEN_THOU_500 = "7500"
        TEN_THOU = "10000"

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
        self.column_dict = {key: False for key in CATEGORY_PATTERNS.keys()}

    def set_search_params(self, zip: str, search_filters: dict[str, Any]) -> None:
        """Set the parameters for searching by ZIP code.

        Args:
            zip (str): the ZIP code
            search_filters (dict[str, Any]): search filters for appending to a gis-csv path
        """
        try:
            region_info = self.get_region_info_from_zipcode(zip)
        except json.JSONDecodeError:
            log(f"Could not decode region info for {zip}.", "warn")
            return None
        except HTTPError:
            log(f"Could not retrieve region info for {zip}.", "warn")
            return None

        if search_filters.get("for sale sold") == "Sold":
            sort_order = self.SortOrder.MOST_RECENTLY_SOLD.value
        else:
            sort_order = self.SortOrder.NEWEST.value
        # TODO make sure to fix filtering so that its not just "single family homes"

        try:
            market = region_info["payload"]["rootDefaults"]["market"]
            region_id = region_info["payload"]["rootDefaults"]["region_id"]
            status = str(region_info["payload"]["rootDefaults"]["status"])
        except KeyError:
            log("Market, region, or status could not be identified ", "warn")
            return None

        self.search_params = {
            "al": 1,
            "has_deal": "false",
            "has_dishwasher": "false",
            "has_laundry_facility": "false",
            "has_laundry_hookups": "false",
            "has_parking": "false",
            "has_pool": "false",
            "has_short_term_lease": "false",
            "include_pending_homes": "false",  # probably an "include" option
            "isRentals": "false",
            "is_furnished": "false",
            "is_income_restricted": "false",
            "is_senior_living": "false",
            "max_year_built": search_filters.get("max year built"),
            "min_year_built": search_filters.get("min year built"),
            "market": market,
            "min_stories": search_filters.get("min stories"),
            "num_homes": 350,
            "ord": sort_order,
            "page_number": "1",
            "pool": "false",
            "region_id": region_id,
            "region_type": "2",
            "status": status,
            "travel_with_traffic": "false",
            "travel_within_region": "false",
            "utilities_included": "false",
            "v": "8",
        }
        if search_filters.get("for sale sold") == "Sold":
            self.search_params["sold_within_days"] = search_filters.get("sold within")
            self.search_params["status"] = 9
        else:
            self.search_params["sf"] = "1, 2, 3, 4, 5, 6, 7"
            match [
                search_filters.get("status coming soon"),
                search_filters.get("status active"),
                search_filters.get("status pending"),
            ]:
                case [True, False, False]:
                    status = "8"
                case [False, True, False]:
                    status = "1"
                case [False, False, True]:
                    status = "130"
                case [True, True, False]:
                    status = "9"
                case [False, True, True]:
                    status = "139"
                case [True, False, True]:
                    status = "138"
                case [True, True, True]:
                    status = "139"

            self.search_params["status"] = status

        if (max_sqft := search_filters.get("max sqft")) != "None":
            self.search_params["max_sqft"] = max_sqft
        if (min_sqft := search_filters.get("min sqft")) != "None":
            self.search_params["min_sqft"] = min_sqft

        if (max_price := search_filters.get("max price")) != "None":
            self.search_params["max_price"] = max_price
        if (min_price := search_filters.get("min price")) != "None":
            self.search_params["min_price"] = min_price

        houses = ""  # figure out how to join into comma string
        if search_filters.get("house type house") is True:
            houses = houses + "1"
        if search_filters.get("house type condo") is True:
            houses = houses + "2"
        if search_filters.get("house type townhouse") is True:
            houses = houses + "3"
        if search_filters.get("house type mul fam") is True:
            houses = houses + "4"

        self.search_params["uipt"] = ",".join(list(houses))

    # redfin setup
    def meta_request_download(self, url: str, search_params) -> str:
        """Method for downloading objects from Redfin.

        Args:
            url (str): the Redfin URL

        Returns:
            str: the unicode text response
        """
        response = requests.get(
            self.rf.base + url, params=search_params, headers=self.rf.user_agent_header
        )
        log(response.request.url, "debug")
        response.raise_for_status()
        return response.text

    def working_below_the_fold(self, property_id: str, listing_id: str = "") -> Any:
        """A below_the_fold method that accepts a listing ID.
        Note:
            If you can get the listing ID, make sure to pass it to this function. You will possibly get incorrect data if you do not pass it

        Args:
            property_id (str): the property ID
            listing_id (str): The listing ID. Defaults to False.

        Returns:
            Any: response
        """
        if listing_id:
            params = {
                "accessLevel": 1,
                "propertyId": property_id,
                "listingId": listing_id,
                "pageType": 1,
            }
        else:
            params = {
                "accessLevel": 1,
                "propertyId": property_id,
                "pageType": 1,
            }
        return self.rf.meta_request("/api/home/details/belowTheFold", params)

    def get_region_info_from_zipcode(self, zip_code: str) -> Any:
        """Get the region ifo from a ZIP code.

        Args:
            zip_code (str): the ZIP code

        Returns:
            Any: response
        """
        return self.rf.meta_request(
            "api/region", {"region_id": zip_code, "region_type": 2, "tz": True, "v": 8}
        )

    def get_gis_csv(self, params: dict[str, Any]) -> str:
        """Get the gis-csv of an area based on the contents of `params`

        Args:
            params (dict[str, Any]): the parameters

        Returns:
            str: the CSV file as a unicode string
        """
        return self.meta_request_download("api/gis-csv", search_params=params)

    # calls stuff
    def get_heating_info_from_super_group(self, super_group: dict) -> list[str]:
        """Extract heating information from a super group

        :
            Must supply a probable heating group for accurate information

            Format of super group in JSON:
            {
                types: []
                amenityGroups: [
                    {
                        groupTitle: ""
                        referenceName : ""
                        amenityEntries : [
                            {
                                amenityName : ""
                                referenceName: ""
                                accessLevel : 1
                                displayLevel : 1
                                amenityValues : []
                            },...
                        ]
                    }
                ]
                titleString: ""
            }

            Format of groupTitle/propertyDetailsHeader on website:
                Interior -> titleString
                ...
                    Heating & Cooling -> groupTitle
                        Electric -> no amenityName
                        Ceiling Fan(s), Programmable Thermostat, Refrigeration -> no amenityName
                        Heating/Cooling Updated In: 2022 -> amenityName = Heating/Cooling Updated In

        Args:
            super_group (dict): the super group to extract terms from

        Returns:
            list[str]: list of heating terms
        """
        amenity_values = []
        for amenity in super_group.get("amenityGroups", ""):  #
            if not any(
                AMENITY_GROUP_INCLUDE_PATTERNS.findall(amenity.get("groupTitle", ""))
            ):
                continue  # this is the name that is bold
            # these are the bulleted items.
            for amenity_entry in amenity.get("amenityEntries", ""):
                # if == "", then item is dangling (no word before colon). give the same treatment to "utilities: ..." as if it were ==""
                amenity_name = amenity_entry.get("amenityName", "")

                if amenity_name and not any(
                    re.compile("utilit", re.I).findall(amenity_name)
                ):
                    # filter the before colon. first if is to have stricter capture rule when amenity item is "Utilities: Natural gas, heat pump, ..."
                    if any(
                        AMENITY_NAME_INCLUDE_PATTERNS.findall(amenity_name)
                    ) and not any(AMENITY_NAME_EXCLUDE_PATTERNS.findall(amenity_name)):
                        amenity_values.extend(
                            [
                                value
                                for value in amenity_entry.get("amenityValues", "")
                                if any(
                                    regex.findall(value)
                                    for regex in AFTER_COLON_FUEL_AND_APPLIANCE_INCLUDE_PATTERNS
                                )
                                and not any(AFTER_COLON_EXCLUDE_PATTERNS.findall(value))
                            ]
                        )
                else:
                    # filter for appliance if dangling or in utilities bullet item
                    amenity_values.extend(
                        [
                            value
                            for value in amenity_entry.get("amenityValues", "")
                            if any(
                                regex.findall(value)
                                for regex in APPLIANCE_HEATING_RELATED_PATTERNS
                            )
                        ]
                    )
        return amenity_values

    def get_super_groups_from_url(self, listing_url: str) -> list | None:
        """Get super group list from listing url.

        Args:
            listing_url (str): The path part of the listing URL. This is without the "redfin.com" part. Include the first forward slash

        Returns:
            list | None: List of all super groups from a Redfin Url. None if an error is encountered or if no super groups were found
        """
        if "redfin" in listing_url:
            listing_url = urlparse(listing_url).path

        try:
            time.sleep(random.uniform(1.2, 2.1))
            initial_info = self.rf.initial_info(listing_url)
        except json.JSONDecodeError:
            log(f"Could not get initial info for {listing_url =}", "warn")
            return None
        try:
            property_id = initial_info["payload"]["propertyId"]
        except KeyError:
            log("Could not find property id", "critical")
            return None
        try:
            listing_id = initial_info["payload"]["listingId"]
        except KeyError:
            listing_id = None
            log(
                "Could not find listing id. Will try to continue. if errors in final zip csv, this might be the issue",
                "warn",
            )
        try:
            time.sleep(random.uniform(1.1, 2.1))
            if listing_id is None:
                mls_data = self.working_below_the_fold(property_id)
            else:
                mls_data = self.working_below_the_fold(property_id, listing_id)
        except json.JSONDecodeError:
            log(f"Could not find mls details for {listing_url = }", "warn")
            return None
        try:
            super_groups = mls_data["payload"]["amenitiesInfo"]["superGroups"]
        except KeyError:
            log(f"Could not find property details for {listing_url = }", "warn")
            return None
        return super_groups

    def get_heating_terms_dict_from_listing(
        self, address_and_url_list: list[str]
    ) -> dict[str, bool]:
        """Generate a filled out dictionary based on `self.column_dict` and the contents of :meth:get_heating_info_from_super_group(address_url_list).

        TODO:
            Since addresses can be doubled and it is random which one gets chosen, just printing listing url so that we can see which one has been chosen

        Args:
            address_and_url_list (list[str]): address in the first position, and the listing URL in the second position

        Returns:
            dict[str, bool]: the filled out `self.column_dict` for the supplied address/listing URL
        """
        address = address_and_url_list[0]
        listing_url = address_and_url_list[1]
        terms = []

        super_groups = self.get_super_groups_from_url(listing_url)
        if super_groups is None:
            log(
                "No amenities found", "info"
            )  # this and "There was no heating information for {address}" should be made in caller?
            return copy.deepcopy(self.column_dict)
        for super_group in super_groups:  # dict
            if any(
                SUPER_GROUP_INCLUDE_PATTERNS.findall(super_group.get("titleString", ""))
            ):
                terms.extend(
                    self.get_heating_info_from_super_group(super_group)
                )  # this will be like [gas, electricity, heat pump]
        if len(terms) == 0:
            log(
                f"There was no heating information for {urlparse(listing_url).path}",
                "info",
            )
            return copy.deepcopy(self.column_dict)

        # categorize the correct dict and return
        master_dict = copy.deepcopy(self.column_dict)
        for input_string in terms:
            log(f"{input_string = }", "debug")
            result = {}
            for key, pattern in CATEGORY_PATTERNS.items():
                if bool(re.search(pattern, input_string)):
                    result[key] = True
                    log(f"Pattern matched on {key, pattern = }", "debug")
                log(f"Pattern did not match on {key, pattern = }", "debug")
            for key in result.keys():
                master_dict[key] = result[key] | master_dict[key]

        # You'll have to df.unnest this for use in a dataframe
        log(f"{terms = }", "debug")
        log(f"{master_dict = }", "debug")
        log(f"Heating amenities found for {address}.", "info")
        return master_dict

    def get_gis_csv_from_zip_with_filters(
        self,
    ) -> pl.DataFrame | None:
        """Clean the GIS CSV retrieved from using the `search_params` field into the desired schema.

        Returns:
            pl.DataFrame | None: returns the DataFrame of cleaned information. None if there was not information in the GIS CSV file.
        """
        if self.search_params is None:
            return
        csv_text = self.get_gis_csv(self.search_params)

        home_types: str = self.search_params.get("uipt", "")
        if "1" in home_types:
            home_types = home_types.replace("1", "Single Family Residential")
        if "2" in home_types:
            home_types = home_types.replace("2", "Condo/Co-op")
        if "3" in home_types:
            home_types = home_types.replace("3", "Townhouse")
        if "4" in home_types:
            home_types = home_types.replace("4", r"Multi-Family \(2-4 Unit\)")

        try:
            df = (
                pl.read_csv(io.StringIO(csv_text), dtypes=self.DESIRED_CSV_SCHEMA)
                .filter(
                    pl.col("PROPERTY TYPE").str.contains(
                        "|".join(home_types.split(","))
                    )
                )
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
                log(
                    "CSV was empty. This can happen if local MLS rules dont allow downloads.",
                    "debug",
                )
                return None
        except Exception as e:
            log(f"Could not read gis csv into dataframe.\n{csv_text = }\n{e}", "warn")
            return None
        return df

    def get_gis_csv_for_zips_in_metro_with_filters(
        self, msa_name: str, search_filters: dict[str, Any]
    ) -> pl.DataFrame | None:
        """Get a DataFrame of all GIS CSVs of a Metropolitan Statistical Area.

        Args:
            msa_name (str): a Metropolitan Statistical Area
            search_filters (dict[str, Any]): filters to search with. generate using :meth:

        Returns:
            pl.DataFrame | None: return a DataFrame of all GIS CSVs retrieved for individual ZIP codes. None if there were no CSVs
        """
        log(f"Searching {msa_name} with filters {search_filters}.", "log")
        zip_codes = metro_name_to_zip_code_list(msa_name)
        formatted_zip_codes = [f"{zip_code:0{5}}" for zip_code in zip_codes]
        log(
            f"Estimated search time: {len(formatted_zip_codes) * (1.75+1.5)}",
            "info",
        )
        list_of_csv_dfs = []
        for zip in formatted_zip_codes:
            time.sleep(random.uniform(1.5, 2))
            self.set_search_params(zip, search_filters)
            temp = self.get_gis_csv_from_zip_with_filters()
            if temp is None:
                log(f"Did not find any houses in {zip}.", "info")
                continue
            log(f"Found data for {temp.height} houses in {zip}.", "info")
            list_of_csv_dfs.append(temp)

        if len(list_of_csv_dfs) == 0:
            return None
        return pl.concat(list_of_csv_dfs)

    def get_house_attributes_from_metro(
        self,
        msa_name: str,
        search_filters: dict[str, Any],
        use_cached_gis_csv_csv: bool = False,
    ) -> None:
        """Main function. Get the heating attributes of a Metropolitan Statistical Area.

        TODO:
            statistics on metropolitan
            Log statistics about the heating outlook of a metro.

        Args:
            msa_name (str): Metropolitan Statistical Area name
            search_filters (dict[str, Any]): search filters
            use_cached_gis_csv_csv (bool, optional): Whether to use an already made GIS CSV DataFrame. Defaults to False.

        Returns:
            None: None if there were no houses found in the metro
        """
        msa_name_file_safe = msa_name.strip().replace(", ", "_").replace(" ", "_")
        metro_output_dir_path = Path(OUTPUT_DIR_PATH) / msa_name_file_safe

        if use_cached_gis_csv_csv:
            log("Loading csv from cache.", "info")
            try:
                search_page_csvs_df = pl.read_csv(
                    metro_output_dir_path / (msa_name_file_safe + ".csv"),
                    dtypes=self.DESIRED_CSV_SCHEMA,
                )
                log(
                    f"Loading csv from {metro_output_dir_path / (msa_name_file_safe + ".csv")} is complete.",
                    "info",
                )
            except FileNotFoundError:
                log(
                    f"Loading csv from {metro_output_dir_path / (msa_name_file_safe + ".csv")} has failed, continuing with API search.",
                    "info",
                )
                search_page_csvs_df = self.get_gis_csv_for_zips_in_metro_with_filters(
                    msa_name, search_filters
                )
        else:
            search_page_csvs_df = self.get_gis_csv_for_zips_in_metro_with_filters(
                msa_name, search_filters
            )

        if search_page_csvs_df is None:
            log(f"No houses found within {msa_name}. Try relaxing filters.", "info")
            return None

        url_col_name = "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
        search_page_csvs_df = search_page_csvs_df.filter(
            (~pl.col(url_col_name).str.contains("(?i)unknown"))
            .and_(pl.col("ADDRESS").str.len_chars().gt(0))
            .and_(pl.col("SQUARE FEET").is_not_null())
            .and_(pl.col("YEAR BUILT").is_not_null())
        )
        # .unique(subset=["LATITUDE", "LONGITUDE"], maintain_order=True)
        # sometimes when there are two of the same listings you'll see the lot and the house. cant determine at this stage, so just leaving duplicates. hopefully this can be handled in viewer
        # also somehow gets GIS-CSV for search pages that dont allow it

        log(f"Found {search_page_csvs_df.height} possible houses in {msa_name}", "info")
        os.makedirs(metro_output_dir_path, exist_ok=True)
        log(
            f"Writing csv for metro to {metro_output_dir_path / (msa_name_file_safe + ".csv")}",
            "debug",
        )
        search_page_csvs_df.write_csv(
            metro_output_dir_path / (msa_name_file_safe + ".csv")
        )

        # go through whole csv and get the house attributes for each house. then partition the dataframe by ZIP and save files

        log("Starting lookups on listing URLS", "info")
        log(
            f"Unique ZIP codes: {search_page_csvs_df["ZIP OR POSTAL CODE"].n_unique()}",
            "info",
        )
        log(
            f"Estimated completion time: {search_page_csvs_df.height * 3.58} seconds",
            "info",
        )

        list_of_dfs_by_zip = search_page_csvs_df.partition_by("ZIP OR POSTAL CODE")

        for df_of_zip in list_of_dfs_by_zip:
            df_of_zip = (
                df_of_zip.with_columns(
                    pl.concat_list([pl.col("ADDRESS"), pl.col(url_col_name)])
                    .map_elements(self.get_heating_terms_dict_from_listing)
                    .alias("nest")
                )
                .drop(url_col_name)
                .unnest("nest")
            )

            zip = df_of_zip.select("ZIP OR POSTAL CODE").item(0, 0)
            df_of_zip.write_csv(f"{metro_output_dir_path}{os.sep}{zip}.csv")

        # log(f"In {msa_name}, there are {} homes with Electric fuel, {} homes with Natural Gas, {} homes with Propane, {} homes with Diesel/Heating Oil, {} homes with Wood/Pellet, {} homes with Solar Heating, {} homes with Heat Pumps, {} homes with Baseboard, {} homes with Furnace, {} homes with Boiler, {} homes with Radiator, {} homes with Radiant Floor")
        log(f"Done with searching houses in {msa_name}!", "info")
