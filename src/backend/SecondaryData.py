import datetime
import os
from enum import Enum, StrEnum
from typing import Any
import json
import pathlib
import re

from backend import Helper
import polars as pl
import polars.selectors as cs
import requests
from dotenv import load_dotenv
# import csv

load_dotenv()
logger = Helper.logger
cache_dir_path = f"{os.path.dirname(__file__)}{os.sep}.cache"
output_dir_path = (
    f"{pathlib.Path(os.path.dirname(__file__)).parent.parent}{os.sep}output"
)

# https://www.dcf.ks.gov/services/PPS/Documents/PPM_Forms/Section_5000_Forms/PPS5460_Instr.pdf
replace_dict = {
    "PercentMarginOfError": "PME",
    "Estimate": "EST",
    "Percent": "PCT",
    "MarginOfError": "MOE",
    "AnnotationOf": "ann",  # have to mess with select logic later down the line to get this shorter
    "AmericanIndian": "_A_",
    "BlackOrAfricanAmerica": "_B_",
    "PacificIslanderIncludingNativeHawaiian": "_P_",
    "Asian": "_S_",
    "White": "_W_",
    "Unknown": "_O_",
    "(?<!Not)HispanicOrLatino": "_H_",  # make sure the way were doing this doesnt cause some race condition
    "NotHispanicOrLatino": "_N_",
    "TotalPopulation": "TPOP",
    "OrMore": "plus",
    "AndOver": "plus",
    "One": "1",
    "Two": "2",
    "Three": "3",
}


class EIADataRetriever:
    """https://www.eia.gov/opendata/pdf/EIA-APIv2-HandsOn-Webinar-11-Jan-23.pdf

    Raises:
        TypeError: _description_
        NotImplementedError: _description_

    Returns:
        _type_: _description_
    """

    # Propane and Heating oil:
    #   *per month is per heating month*
    class EnergyTypes(Enum):
        PROPANE = 1
        NATURAL_GAS = 2
        ELECTRICITY = 3
        HEATING_OIL = 4

    class PetroleumProductTypes(StrEnum):
        NATURAL_GAS = "EPG0"
        PROPANE = "EPLLPA"
        HEATING_OIL = "EPD2F"

    class FuelBTUConversion(Enum):
        # https://www.edf.org/sites/default/files/10071_EDF_BottomBarrel_Ch3.pdf
        # https://www.eia.gov/energyexplained/units-and-calculators/british-thermal-units.php
        # https://www.eia.gov/energyexplained/units-and-calculators/
        NO1_OIL_BTU_PER_GAL = 135000
        NO2_OIL_BTU_PER_GAL = 140000
        NO4_OIL_BTU_PER_GAL = 146000
        NO5_OIL_BTU_PER_GAL = 144500
        NO6_OIL_BTU_PER_GAL = 150000
        HEATING_OIL_BTU_PER_GAL = 138500
        ELECTRICITY_BTU_PER_KWH = 3412.14
        # 1000 cubic feet
        NG_BTU_PER_MCT = 1036
        NG_BTU_PER_THERM = 100000
        PROPANE_BTU_PER_GAL = 91452
        WOOD_BTU_PER_CORD = 20000000

    def __init__(self):
        self.eia_base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")
        if self.api_key is None:
            logger.critical(
                "No Census API key found in a .env file in project directory. please request a key at https://www.eia.gov/opendata/register.php"
            )
            exit()

    # normalize prices
    #!this should be failing?
    def _price_per_btu_converter(
        self, energy_price_dict: dict
    ) -> dict[str, str | EnergyTypes | float]:
        """Convert an energy source's price per quantity into price per BTU.

        Args:
            energy_source (_type_): energy source json

        Returns:
            dict: new dictionary with btu centric pricing
        """
        # https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf
        # Natural gas: $13.86 per thousand cubic feet /1.036 million Btu per thousand cubic feet = $13.38 per million Btu
        #! currently doesn't take into account efficiency: make new function based on burner type/ end usage type
        #! double check money units
        btu_dict = {}
        factor = 1
        CENTS_IN_DOLLAR = 100
        match energy_price_dict.get("type"):
            case self.EnergyTypes.PROPANE:
                factor = self.FuelBTUConversion.PROPANE_BTU_PER_GAL
            case self.EnergyTypes.NATURAL_GAS:
                factor = self.FuelBTUConversion.NG_BTU_PER_MCT
            case self.EnergyTypes.ELECTRICITY:
                factor = (
                    self.FuelBTUConversion.ELECTRICITY_BTU_PER_KWH.value
                    / CENTS_IN_DOLLAR
                )
            case self.EnergyTypes.HEATING_OIL:
                factor = self.FuelBTUConversion.HEATING_OIL_BTU_PER_GAL

        for key, value in energy_price_dict.items():
            if key in ["type", "state"]:
                btu_dict[key] = value
                continue
            btu_dict[key] = value / factor

        return btu_dict

    # api to dict handler Helpers
    def price_dict_to_clean_dict(
        self, eia_json: dict, energy_type: EnergyTypes, state: str
    ) -> dict[str, str | EnergyTypes | float]:
        """Clean JSON data returned by EIA's API.

        Args:
            eia_json (_type_): the dirty JSON

        Returns:
            dict: cleaned JSON with state and energy type
        """
        # price key is different for electricity
        accessor = "value"
        if "product" not in eia_json["response"]["data"][0]:
            accessor = "price"

        result_dict = {
            entry["period"]: entry[f"{accessor}"]
            for entry in eia_json["response"]["data"]
        }
        result_dict["type"] = energy_type
        result_dict["state"] = state

        return result_dict

    def price_df_to_clean_dict(
        self, eia_df: pl.DataFrame, energy_type: EnergyTypes, state: str
    ) -> dict[str, str | EnergyTypes | float]:
        """Clean DataFrame data consisting of EIA API data.

        Args:
            eia_df (pl.DataFrame): the DataFrame to clean
            energy_type (EnergyTypes): the energy type
            state (str): the state

        Returns:
            dict[str, str|EnergyTypes|float]: the dict
        """
        result_dict = {}
        for row in eia_df.rows(named=True):
            year_month = f"{row.get("year")}-{row.get("month")}"
            result_dict[year_month] = round(row.get("monthly_avg_price"), 3)  # type: ignore
        result_dict["type"] = energy_type
        result_dict["state"] = state
        return result_dict

    # api to dict handler
    def price_to_clean_dict(
        self, price_struct: dict | pl.DataFrame, energy_type: EnergyTypes, state: str
    ) -> dict[str, str | EnergyTypes | float]:
        """Handle the different data types that EIA data could be stored in.

        Args:
            price_struct (dict | pl.DataFrame): a data structure containing the year, month, and price info
            energy_type (EnergyTypes): the energy type
            state (str): the state

        Raises:
            TypeError: raised if the type of `price_struct` is not supported

        Returns:
            dict[str, str|EnergyTypes|float]: the normalized and structured data in dict form
        """
        match price_struct:
            case dict():
                return self.price_dict_to_clean_dict(price_struct, energy_type, state)
            case pl.DataFrame():
                return self.price_df_to_clean_dict(price_struct, energy_type, state)
            case _:
                raise TypeError(f"Type not supported: {type(energy_type)}")

    # api interaction
    def monthly_electricity_price_per_kwh(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict[str, Any]:
        """Get a state's average monthly energy price in cents per KWh.

        Args:
            state (str): the 2 character postal code of a state
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: the dictionary in `year-month: price` form
        """
        # cent/ kwh
        url = f"{self.eia_base_url}/electricity/retail-sales/data?data[]=price&facets[sectorid][]=RES&facets[stateid][]={state}&frequency=monthly&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = Helper.req_get_wrapper(url)
        eia_request.raise_for_status()

        return eia_request.json()

    def monthly_ng_price_per_mcf(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict[str, Any]:
        """Get a state's average natural gas price in dollars per MCF.

        Args:
            state (str): the 2 character postal code of a state
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # $/mcf
        url = f"https://api.eia.gov/v2/natural-gas/pri/sum/data/?frequency=monthly&data[0]=value&facets[duoarea][]=S{state}&facets[process][]=PRS&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = Helper.req_get_wrapper(url)
        eia_request.raise_for_status()

        return eia_request.json()

    def monthly_heating_season_heating_oil_price_per_gal(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> pl.DataFrame:
        """Get a participating state's average heating oil price in dollars per gal.

        Note:
            Only certain states are tracked.

        Args:
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=weekly&data[0]=value&facets[duoarea][]=S{state}&facets[product][]=EPD2F&start={start_date}&end={end_date}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = Helper.req_get_wrapper(url)
        eia_request.raise_for_status()

        json = eia_request.json()
        # return self.price_json_to_dict(eia_request.json())
        df = pl.DataFrame(json["response"]["data"])
        # df = df.with_columns(pl.col("period").str.to_date().alias("period"))
        df = df.with_columns(pl.col("period").str.strptime(pl.Date))
        df = df.with_columns(
            pl.col("period").dt.year().alias("year"),
            pl.col("period").dt.month().alias("month"),
        )

        monthly_avg_price = (
            df.group_by(["year", "month"])
            .agg(pl.col("value").mean().alias("monthly_avg_price"))
            .sort("year", "month")
        )

        return monthly_avg_price

    def monthly_heating_season_propane_price_per_gal(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> pl.DataFrame:
        """Get a participating state's average propane price in dollars per gal.

        Note:
            Only certain states are tracked.

        Args:
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=weekly&data[0]=value&facets[duoarea][]=S{state}&facets[product][]=EPLLPA&start={start_date}&end={end_date}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = Helper.req_get_wrapper(url)
        eia_request.raise_for_status()

        json = eia_request.json()
        # return self.price_json_to_dict(eia_request.json())
        df = pl.DataFrame(json["response"]["data"])
        # df = df.with_columns(pl.col("period").str.to_date().alias("period"))
        df = df.with_columns(pl.col("period").str.strptime(pl.Date))
        df = df.with_columns(
            pl.col("period").dt.year().alias("year"),
            pl.col("period").dt.month().alias("month"),
        )

        monthly_avg_price = (
            df.group_by(["year", "month"])
            .agg(pl.col("value").mean().alias("monthly_avg_price"))
            .sort("year", "month")
        )

        return monthly_avg_price

    def monthly_price_per_btu_by_energy_type(
        self,
        energy_type: EnergyTypes,
        state: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[str, str | EnergyTypes | float]:
        """Get the cost per BTU for the given energy type for the state, over the given period of time. Refer to EIA's documentation
        for changes to data collection during certain years.

        Args:
            energy_type (EnergyTypes): The energy type
            state (str): the 2 character postal abbreviation. Note that for heating oil, only certain states have this information collected
            start_date (datetime.date): the date for which to start the search. Inclusive. Not that for heating oil, only heating months will be returned
            end_date (datetime.date): the date for which to end the search. Non inclusive

        Raises:
            NotImplementedError: Invalid energy type

        Returns:
            dict: year-month: price in USD to BTU
        """
        match energy_type:
            case self.EnergyTypes.PROPANE:
                return self._price_per_btu_converter(
                    self.price_to_clean_dict(
                        self.monthly_heating_season_propane_price_per_gal(
                            state, start_date, end_date
                        ),
                        energy_type,
                        state,
                    )
                )
            case self.EnergyTypes.NATURAL_GAS:
                return self._price_per_btu_converter(
                    self.price_to_clean_dict(
                        self.monthly_ng_price_per_mcf(state, start_date, end_date),
                        energy_type,
                        state,
                    )
                )
            case self.EnergyTypes.ELECTRICITY:
                return self._price_per_btu_converter(
                    self.price_to_clean_dict(
                        self.monthly_electricity_price_per_kwh(
                            state, start_date, end_date
                        ),
                        energy_type,
                        state,
                    )
                )
            case self.EnergyTypes.HEATING_OIL:
                return self._price_per_btu_converter(
                    self.price_to_clean_dict(
                        self.monthly_heating_season_heating_oil_price_per_gal(
                            state, start_date, end_date
                        ),
                        energy_type,
                        state,
                    )
                )
            case _:
                raise NotImplementedError(f"Unsupported energy type: {energy_type}")


class CensusAPI:
    """https://api.census.gov/data/2019/acs/acs5.html"""

    def __init__(self) -> None:
        self.base_url = "https://data.census.gov/"
        # https://api.census.gov/data/2021/acs/acs5/profile/variables.html
        self.api_key = os.getenv("CENSUS_API_KEY")
        if self.api_key is None:
            logger.critical(
                "No Census API key found in a .env file in project directory. please request a key at https://api.census.gov/data/key_signup.html"
            )
            exit()
        self.MAX_COL_NAME_LENGTH = 80

    def get(self, url: str) -> requests.Response | None:
        r = requests.get(url, timeout=65)
        if r.status_code == 400:
            logger.info(f"Unknown variable {r.text.split("variable ")[-1]}")
            return None
        return r

    def get_and_cache_data(
        self, file_name: str, url_to_lookup_on_miss: str
    ) -> dict[str, str] | bool:
        """Cache files in the .cache folder

        Args:
            file_name (str): file name to save/lookup
            url_to_lookup_on_miss (str): the Census url to lookup

        Returns:
            bool | dict[str, str] | None | Any: the dict of tablename:label or
        """
        try:
            os.mkdir(cache_dir_path)
        except FileExistsError:
            logger.debug("Cache folder exists.")
        except FileNotFoundError:
            logger.debug("Parent folder for cache folder does not exist.")

        my_json = None

        try:
            with open(f"{cache_dir_path}{os.sep}{file_name}", mode="r") as f:
                logger.debug(f"Reading {file_name}")
                try:
                    my_json = json.load(f)
                except json.JSONDecodeError:
                    logger.error("Could not decode cached file")
                    return False
        except FileNotFoundError:
            req = self.get(url_to_lookup_on_miss)
            if req is None:
                logger.info(f"{req = }")
                return False
            req.raise_for_status()
            my_json = req.json()
            with open(f"{cache_dir_path}{os.sep}{file_name}", "w") as f:
                json.dump(my_json, f)

        return my_json

    def get_race_makeup_by_zcta(self, zcta: str) -> str | None:
        """Get race make up by zcta from

        Note:
            use `get_table_group_for_zcta_by_state_by_year`

        Args:
            zcta (str): zcta

        Returns:
            str | None: text or none
        """
        # get white, black, american indian/native alaskan, asian, NH/PI, other. note that these are estimates, margin of error can be had with "M"
        req = self.get(
            f"https://api.census.gov/data/2021/acs/acs5/profile?get=DP05_0064E,DP05_0065E,DP05_0066E,DP05_0067E,DP05_0068E,DP05_0069E&for=zip%20code%20tabulation%20area:{zcta}&key={self.api_key}"
        )
        if req is None:
            return None
        return req.text

    def get_acs5_profile_table_to_group_name(
        self, table: str, year: str
    ) -> dict[str, Any] | None:
        """Get a JSON representation of a table's attributes.

        Note:
            Tables must be:
                * DP02
                * DP02PR
                * DP03
                * DP04
                * DP05

            Returned object will have entries similar to:
            ```json
            "DP05_0037M": {
                "label": "Margin of Error!!RACE!!Total population!!One race!!White",
                "concept": "ACS DEMOGRAPHIC AND HOUSING ESTIMATES",
                "predicateType": "int",
                "group": "DP05",
                "limit": 0,
                "predicateOnly": true
            }
            ```

        Args:
            table (str): the table to lookup
            year (str): which acs5 year to look up

        Returns:
            str | Any: json object
        """
        cache_file_rel_path = f"{year}-acs5-profile-groups-{table}.json"
        groups_url = (
            f"https://api.census.gov/data/{year}/acs/acs5/profile/groups/{table}.json"
        )
        groups_to_label_translation = self.get_and_cache_data(
            cache_file_rel_path, groups_url
        )
        if groups_to_label_translation is False:
            logger.warning("Something is wrong with groups label dict")
            return None
        return groups_to_label_translation["variables"]  # type: ignore

    def translate_and_truncate_unique_acs5_profile_groups_to_labels_for_header_list(
        self, headers: list[str], table: str, year: str
    ) -> None:
        """Gets the label name for a table and row for the acs5 profile surveys.

        Args:
            table_and_row (str): the presumed table and row, along with selector at the end
            year (str): the year

        Returns:
            None: translates the list of table_row_selector to its english label
        """
        # is going to read the file multiple times, save last req as {"table": req_json[table]...} for this?
        groups_to_label_translation_dict = self.get_acs5_profile_table_to_group_name(
            table, year
        )
        if groups_to_label_translation_dict is None:
            logger.warning("Could not translate headers")
            return groups_to_label_translation_dict

        for idx, header in enumerate(headers):
            new_col_name_dict = groups_to_label_translation_dict.get(header)
            if new_col_name_dict is None:
                # returns none if not in dict, means we have custom name and can continue
                continue
            new_col_name = new_col_name_dict["label"]
            # qgis doesnt allow field names of 80+ chars. massage into form, then cut off
            # delimiter for table subsection
            new_col_name = re.sub("!!", " ", new_col_name)
            new_col_name = re.sub(r"\s+", " ", new_col_name)
            # easier to read
            new_col_name_parts = new_col_name.split(" ")
            for idy, no_format in enumerate(new_col_name_parts):
                new_col_name_parts[idy] = no_format.capitalize()
            new_col_name = "".join(new_col_name_parts)
            # shortenings to fit length requirement
            for key, value in replace_dict.items():
                new_col_name = re.sub(key, value, new_col_name)
            # limiter
            new_col_name = new_col_name[
                : min(len(new_col_name), self.MAX_COL_NAME_LENGTH)
            ]

            if new_col_name not in headers[:idx]:
                headers[idx] = new_col_name

    def get_acs5_profile_table_group_for_zcta_by_year(
        self, table: str, year: str
    ) -> bool:
        """csv output of a acs 5 year profile survey table

        Args:
            table (str): census demo acs5 table
            year (str): year to search
            state (str): state
        """
        cache_file_rel_path = f"{os.sep}{year}-acs-profile-table-{table}.json"
        url = f"https://api.census.gov/data/{year}/acs/acs5/profile?get=group({table})&for=zip%20code%20tabulation%20area:*"
        list_of_list_table_json = self.get_and_cache_data(cache_file_rel_path, url)

        if list_of_list_table_json is False:
            logger.warning(
                f"Could not load table {table}. Perhaps the api is down or there was an error saving/reading the file."
            )
            return False

        self.translate_and_truncate_unique_acs5_profile_groups_to_labels_for_header_list(
            list_of_list_table_json[0], # type: ignore
            table,
            year,  # type: ignore
        )

        df = pl.DataFrame(list_of_list_table_json, orient="row")
        # funky stuff to get the first list to be the name of the columns
        df = (
            df.rename(df.head(1).to_dicts().pop())
            .slice(1)  # type: ignore
            .drop("NAME", cs.matches("(?i)^(ann)"), cs.matches(f"(?i){table}"))
            .rename({"zip code tabulation area": "ZCTA"})
            .cast(
                {
                    "ZCTA": pl.Int32,
                }
            )
        )
        df.write_csv(f"{output_dir_path}{os.sep}acs5-profile-group-{table}-zcta.csv")
        return True

    # b
    def get_acs5_subject_table_to_group_name(
        self, table: str, year: str
    ) -> dict[str, Any] | None:
        """Get a JSON representation of a table's attributes.

        Note:
            Tables must be:
                * DP02
                * DP02PR
                * DP03
                * DP04
                * DP05

            Returned object will have entries similar to:
            ```json
            "DP05_0037M": {
                "label": "Margin of Error!!RACE!!Total population!!One race!!White",
                "concept": "ACS DEMOGRAPHIC AND HOUSING ESTIMATES",
                "predicateType": "int",
                "group": "DP05",
                "limit": 0,
                "predicateOnly": true
            }
            ```

        Args:
            table (str): the table to lookup
            year (str): which acs5 year to look up

        Returns:
            str | Any: json object
        """
        cache_file_rel_path = f"{year}-acs5-subject-groups-{table}.json"
        groups_url = (
            f"https://api.census.gov/data/{year}/acs/acs5/subject/groups/{table}.json"
        )
        groups_to_label_translation = self.get_and_cache_data(
            cache_file_rel_path, groups_url
        )
        if groups_to_label_translation is False:
            logger.warning("Something is wrong with groups label dict")
            return None
        return groups_to_label_translation["variables"]  # type: ignore

    def translate_and_truncate_unique_acs5_subject_groups_to_labels_for_header_list(
        self, headers: list[str], table: str, year: str
    ) -> None:
        """Gets the label name for a table and row for the acs5 profile surveys.

        Args:
            table_and_row (str): the presumed table and row, along with selector at the end
            year (str): the year

        Returns:
            None: translates the list of table_row_selector to its english label
        """
        # is going to read the file multiple times, save last req as {"table": req_json[table]...} for this?
        groups_to_label_translation_dict = self.get_acs5_subject_table_to_group_name(
            table, year
        )
        if groups_to_label_translation_dict is None:
            logger.warning("Could not translate headers")
            return groups_to_label_translation_dict

        for idx, header in enumerate(headers):
            new_col_name_dict = groups_to_label_translation_dict.get(header)
            if new_col_name_dict is None:
                # returns none if not in dict, means we have custom name and can continue
                continue
            new_col_name = new_col_name_dict["label"]
            # qgis doesnt allow field names of 80+ chars. massage into form, then cut off
            # delimiter for table subsection
            new_col_name = re.sub("!!", " ", new_col_name)
            new_col_name = re.sub(r"\s+", " ", new_col_name)
            # easier to read
            new_col_name_parts = new_col_name.split(" ")
            for idy, no_format in enumerate(new_col_name_parts):
                new_col_name_parts[idy] = no_format.capitalize()
            new_col_name = "".join(new_col_name_parts)
            # shortenings to fit length requirement
            for key, value in replace_dict.items():
                new_col_name = re.sub(key, value, new_col_name)
            # limiter
            new_col_name = new_col_name[
                : min(len(new_col_name), self.MAX_COL_NAME_LENGTH)
            ]

            if new_col_name not in headers[:idx]:
                headers[idx] = new_col_name

    def get_acs5_subject_table_group_for_zcta_by_year(
        self, table: str, year: str
    ) -> bool:
        """csv output of a acs 5 year subject survey table

        Args:
            table (str): census demo acs5 table
            year (str): year to search
            state (str): state
        """
        cache_file_rel_path = f"{os.sep}{year}-acs-subject-table-{table}.json"
        url = f"https://api.census.gov/data/{year}/acs/acs5/subject?get=group({table})&for=zip%20code%20tabulation%20area:*"
        list_of_list_table_json = self.get_and_cache_data(cache_file_rel_path, url)

        if list_of_list_table_json is False:
            logger.warning(
                f"Could not load table {table}. Perhaps the api is down or there was an error saving/reading the file."
            )
            return False

        self.translate_and_truncate_unique_acs5_subject_groups_to_labels_for_header_list(
            list_of_list_table_json[0], # type: ignore
            table,
            year,  # type: ignore
        )

        df = pl.DataFrame(list_of_list_table_json, orient="row")
        # funky stuff to get the first list to be the name of the columns
        df = (
            df.rename(df.head(1).to_dicts().pop())
            .slice(1)  # type: ignore
            .drop("NAME", cs.matches("(?i)^(ann)"), cs.matches(f"(?i){table}"))
            .rename({"zip code tabulation area": "ZCTA"})
            .cast(
                {
                    "ZCTA": pl.Int32,
                }
            )
        )
        df.write_csv(f"{output_dir_path}{os.sep}acs5-subject-group-{table}-zcta.csv")
        return True
