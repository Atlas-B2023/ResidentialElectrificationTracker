import copy
import io

# import itertoos
import os
import random
import re
import time
import json

# from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse

import polars as pl
import redfin
import requests
from backend import (
    # ASCIIColors,
    logger,
    metro_name_to_zip_code_list,
)


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

utilities_group = re.compile(
    r"electric(?=\s(heat|baseboard))", re.I
)  # only match electric in utilities container with this matches

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

OUTPUT_DIR_PATH = f"{Path(os.path.dirname(__file__)).parent.parent}{os.sep}output"


class RedfinApi:
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
        self.column_dict = {key: False for key in regex_category_patterns.keys()}

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
        except json.JSONDecodeError:
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

    # redfin stuff
    def meta_request_download(self, url, kwargs) -> str:
        """Method for downloading objects.

        Notes:
            Use for downloading the gis csv

        Args:
            url (_type_): _description_
            kwargs (_type_): _description_

        Returns:
            str: _description_
        """
        response = requests.get(
            self.rf.base + url, params=kwargs, headers=self.rf.user_agent_header
        )
        logger.debug(response.request.url)  # change to debug
        response.raise_for_status()
        return response.text

    def working_below_the_fold(self, property_id, listing_id):
        return self.rf.meta_request(
            "/api/home/details/belowTheFold",
            {
                "accessLevel": 1,
                "propertyId": property_id,
                "listingId": listing_id,
                "pageType": 1,
            },
        )

    def get_region_info_from_zipcode(self, zip_code: str) -> Any:
        return self.rf.meta_request(
            "api/region", {"region_id": zip_code, "region_type": 2, "tz": True, "v": 8}
        )

    def get_gis_csv(self, params) -> str:
        return self.meta_request_download("api/gis-csv", params)

    # api calls stuff
    def get_heating_info_from_super_group(self, super_group: dict) -> list[str]:
        """Supply a probable heating group

        Notes:
            Format of super group :
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

        Args:
            super_group (dict): _description_

        Returns:
            list[str]: list of raw heating terms
        """
        reference_names = [
            "(?i)HEATING",
            "HEATING_FUEL",
            "UTILITIES",
            "utili",
            "heat",
        ]

        raw_amenity_values = []
        # list. skip for loop if nothing
        amenity_groups = super_group.get("amenityGroups", "")
        # going through all super  and check if property detail header is a match.
        for amenity in amenity_groups:
            for amenity_entry in amenity.get("amenityEntries", ""):
                if any(
                    re.findall(
                        "|".join(reference_names),
                        amenity_entry.get("referenceName", ""),
                    )
                ):
                    if re.match(r"utili", amenity_entry.get("amenityName", ""), re.I):
                        temp_list = []
                        for string in amenity_entry.get("amenityValues", ""):
                            match = utilities_group.findall(
                                string
                            )  # utilities is weird since they pack everting together
                            if match:
                                temp_list.extend(utilities_group.findall(string))
                        raw_amenity_values.extend(temp_list)
                    else:
                        raw_amenity_values.extend(amenity_entry.get("amenityValues"))
                elif any(
                    re.findall(
                        "|".join(reference_names), amenity.get("referenceName", "")
                    )
                ):
                    if re.match(r"utili", amenity.get("referenceName", ""), re.I):
                        temp_list = []
                        for string in amenity_entry.get("amenityValues", ""):
                            match = utilities_group.findall(
                                string
                            )  # utilities is weird since they pack everting together
                            if match:
                                temp_list.extend(utilities_group.findall(string))
                        raw_amenity_values.extend(temp_list)
                    else:
                        raw_amenity_values.extend(amenity_entry.get("amenityValues"))

        amenity_values = [
            string
            for string in raw_amenity_values
            if any(regex.findall(string) for regex in heating_related_patterns)
            and not any(regex.findall(string) for regex in exclude_terms)
        ]
        return amenity_values

    def get_super_groups_from_url(self, listing_url: str) -> list | None:
        """Super group list from listing url.

        Args:
            listing_url (str): The path to the house. This is without the "redfin.com" part

        Returns:
            list | None: List of all super groups from a redfin url. None if there an error is encountered or no super groups were found
        """
        if "redfin" in listing_url:
            listing_url = urlparse(listing_url).path

        try:
            time.sleep(random.uniform(1.2, 2.1))
            initial_info = self.rf.initial_info(listing_url)
        except json.JSONDecodeError:
            logger.warn(f"Could not get initial info for {listing_url =}")
            return None
        property_id = initial_info["payload"]["propertyId"]
        listing_id = initial_info["payload"]["listingId"]
        try:
            time.sleep(random.uniform(1.1, 2.1))
            mls_data = self.working_below_the_fold(property_id, listing_id)
        except json.JSONDecodeError:
            logger.warn(f"Could not find mls details for {listing_url = }")
            return None
        try:
            super_groups = mls_data["payload"]["amenitiesInfo"]["superGroups"]
        except KeyError:
            logger.warn(f"Could not find property details for {listing_url = }")
            return None
        return super_groups

    def get_heating_terms_dict_from_listing(
        self, address_url_list: list[str]
    ) -> dict[str, bool]:
        address = address_url_list[0]
        listing_url = address_url_list[1]
        terms = []

        super_groups = self.get_super_groups_from_url(listing_url)
        if super_groups is None:
            logger.info(
                "No amenities found"
            )  # this and "There was no heating information for {address}" should be made in caller?
            return copy.deepcopy(self.column_dict)
        for super_group in super_groups:  # dict
            terms.extend(
                self.get_heating_info_from_super_group(super_group)
            )  # this will be like [gas, electricity, heat pump]
        if len(terms) == 0:
            logger.info(f"There was no heating information for {address}")
            return copy.deepcopy(self.column_dict)

        # categorize the correct dict and return
        master_dict = copy.deepcopy(self.column_dict)
        logger.debug(f"master dict {master_dict = }")
        for input_string in terms:
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
        logger.debug(terms)
        logger.debug(master_dict)
        logger.info(f"Heating amenities found for {address}.")
        return master_dict

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
                logger.debug(
                    "CSV was empty. This can happen if local MLS rules dont allow downloads."
                )
                return None
        except Exception as e:
            logger.warning(
                f"Could not read gis csv into dataframe.\n{csv_text = }\n{e}"
            )
            return None
        return df

    def get_gis_csv_for_zips_in_metro_with_filters(
        self,
        msa_name: str,
        min_year_built: str,
        max_year_built: str,
        min_stories: Stories,
        sort_order: SortOrder,
        home_types: list[HouseType],
        sold: SoldWithinDays | None = SoldWithinDays.FIVE_YEARS,
    ) -> pl.DataFrame | None:
        """Get DataFrame of all gis CSVs of a metro.

        Args:
            metro (str): MSA name
            min_year_built (str): min year built to filter
            max_year_built (str): max year built to filter
            min_stories (Stories): min stories to filter
            sort_order (SortOrder): how to sort results. Max 350 results, suggested to sort by recent sold
            home_types (list[HouseType]): House type
            sold (SoldWithinDays | None, optional): Sold within days. Defaults to SoldWithinDays.FIVE_YEARS.

        Returns:
            pl.DataFrame | None: Return a dataframe of all gis CSVs in the metro . Return `None` if no houses are found in the metro
        """
        zip_codes = metro_name_to_zip_code_list(msa_name)
        formatted_zip_codes = [f"{zip_code:0{5}}" for zip_code in zip_codes]
        logger.info(f"Estimated search time: {len(formatted_zip_codes) * (1.75+1.5)}")
        list_of_csv_dfs = []
        for zip in formatted_zip_codes:
            time.sleep(random.uniform(1.5, 2))
            self.set_search_params(
                zip,
                min_year_built,
                max_year_built,
                min_stories,
                sort_order,
                home_types,
                sold,
            )
            temp = self.get_gis_csv_from_zip_with_filters()
            if temp is None:
                logger.info(f"Did not find any houses in {zip}.")
                continue
            logger.info(f"Found data for {temp.height} houses in {zip}.")
            list_of_csv_dfs.append(temp)

        if len(list_of_csv_dfs) == 0:
            return None
        return pl.concat(list_of_csv_dfs)

    def get_house_attributes_from_metro(
        self,
        msa_name: str,
        min_year_built: str,
        max_year_built: str,
        min_stories: Stories,
        sort_order: SortOrder,
        home_types: list[HouseType],
        sold: SoldWithinDays | None = SoldWithinDays.FIVE_YEARS,
        use_cached_gis_csv_csv: bool = False,
    ) -> pl.DataFrame | None:
        msa_name_file_safe = msa_name.strip().replace(", ", "_").replace(" ", "_")
        metro_output_dir_path = Path(OUTPUT_DIR_PATH) / msa_name_file_safe

        if use_cached_gis_csv_csv:
            logger.info("Loading csv from cache.")
            search_page_csvs_df = pl.read_csv(
                metro_output_dir_path / (msa_name_file_safe + ".csv"),
                dtypes=self.DESIRED_CSV_SCHEMA,
            )
            if search_page_csvs_df is not None:
                logger.info(
                    f"Loading csv from {metro_output_dir_path / (msa_name_file_safe + ".csv")} is complete."
                )
            else:
                logger.info(
                    f"Loading csv from {metro_output_dir_path / (msa_name_file_safe + ".csv")} has failed."
                )
                return
        else:
            search_page_csvs_df = self.get_gis_csv_for_zips_in_metro_with_filters(
                msa_name,
                min_year_built,
                max_year_built,
                min_stories,
                sort_order,
                home_types,
                sold,
            )
        if search_page_csvs_df is None:
            logger.info(f"No houses found within {msa_name}. Try relaxing filters.")
            return None

        url_col_name = "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
        search_page_csvs_df = search_page_csvs_df.filter(
            (~pl.col(url_col_name).str.contains("(?i)unknown")).and_(
                pl.col("ADDRESS").str.len_chars().gt(0)
            )
        )

        os.makedirs(metro_output_dir_path, exist_ok=True)
        # write it so that we can save for future use
        logger.debug(
            f"writing csv for metro to {metro_output_dir_path / (msa_name_file_safe + ".csv")}"
        )
        search_page_csvs_df.write_csv(
            metro_output_dir_path / (msa_name_file_safe + ".csv")
        )

        # go through whole csv and get the house attributes for each house. then partition the dataframe by ZIP and save files

        logger.info("Starting lookups on listing URLS")
        # can have more than 1 zip in csv. save file, then append each listing?
        logger.info(
            f"Unique ZIP codes: {search_page_csvs_df["ZIP OR POSTAL CODE"].n_unique()}"
        )
        logger.info(
            f"Estimated completion time: {search_page_csvs_df.height * 3.58} seconds"
        )  # make another estimation for csvs

        list_of_dfs_by_zip = search_page_csvs_df.partition_by("ZIP OR POSTAL CODE")

        for df_of_zip in list_of_dfs_by_zip:
            df_of_zip = (
                df_of_zip.with_columns(
                    pl.concat_list(
                        [pl.col("ADDRESS"), pl.col(url_col_name)]
                    )  # len check wont work. just leave that out and make sure filter of search page csv is good
                    .map_elements(self.get_heating_terms_dict_from_listing)
                    .alias("nest")
                )
                .drop(url_col_name)
                .unnest("nest")
            )

            zip = df_of_zip.select("ZIP OR POSTAL CODE").item(0, 0)
            df_of_zip.write_csv(f"{metro_output_dir_path}{os.sep}{zip}.csv")

        logger.info(f"Done with searching houses in {msa_name}!")
