import datetime
import os
from enum import Enum, StrEnum
from typing import Any
import json
import pathlib

import us.states as sts
import Helper as Helper
import polars as pl
import polars.selectors as cs
import requests
from dotenv import load_dotenv
# import csv

load_dotenv()
logger = Helper.logger


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

    def _monthly_heating_season_propane_price_per_gal(
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
                        self._monthly_heating_season_propane_price_per_gal(
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
    def __init__(self) -> None:
        self.base_url = "https://data.census.gov/"
        # https://api.census.gov/data/2021/acs/acs5/profile/variables.html
        self.api_key = os.getenv("CENSUS_API_KEY")

    def get(self, url: str) -> requests.Response | None:
        r = requests.get(url, timeout=15)
        if r.status_code == 400:
            logger.info(f"Unknown variable {r.text.split("variable ")[-1]}")
            return None
        return r

    def get_race_makeup_by_zcta(self, zcta: str) -> str | None:
        # get white, black, american indian/native alaskan, asian, NH/PI, other. note that these are estimates, margin of error can be had with "M"
        req = self.get(
            f"https://api.census.gov/data/2021/acs/acs5/profile?get=DP05_0064E,DP05_0065E,DP05_0066E,DP05_0067E,DP05_0068E,DP05_0069E&for=zip%20code%20tabulation%20area:{zcta}&key={self.api_key}"
        )
        if req is None:
            return None
        return req.text

    def get_table_to_group_name(self, table: str, year: str) -> dict[str, Any] | Any:
        """Get a JSON representation of a table's attributes.

        Note:
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
        # check cache. file name is {year}-acs-groups-{table}
        # make cache a func
        cache_file_rel_path = f"{os.path.dirname(__file__)}{os.sep}.cache{os.sep}{year}-acs-groups-{table}.json"
        if os.path.exists(cache_file_rel_path):
            with open(cache_file_rel_path, "r") as f:
                logger.debug(f"cache for {cache_file_rel_path} being read.")
                return json.load(f)["variables"]

        logger.debug(f"making request and caching {cache_file_rel_path}.")
        req = self.get(
            f"https://api.census.gov/data/{year}/acs/acs5/profile/groups/{table}.json"
        )
        if req is None:
            return None
        req.raise_for_status()
        req_json = req.json()
        with open(cache_file_rel_path, "w") as f:
            json.dump(req_json, f)

        return req_json["variables"]

    def translate_unique_groups_to_labels_for_header_list(
        self, headers: list[str], table: str, year: str
    ) -> str | Any:
        """Gets the label name for a table and group row for the acs5 surveys.

        Args:
            table_and_row (str): the presumed table and row, along with selector at the end
            year (str): the year

        Returns:
            str | Any: _description_
        """
        # is going to read the file multiple times, save last req as {"table": req_json[table]...} for this?
        req_json = self.get_table_to_group_name(table, year)
        if req_json is None:
            return req_json
        for idx, header in enumerate(headers):
            new_head_dict = req_json.get(header)
            if new_head_dict is None:
                # returns none if not in dict, means we have custom name and can continue
                continue
            new_head = new_head_dict["label"]
            if new_head not in headers[:idx]:
                headers[idx] = new_head

    def get_table_group_for_zcta_by_state_by_year(
        self, table: str, year: str, state: str
    ):
        """csv output

        Args:
            table (str): census demo acs5 table
            year (str): year to search
            state (str): state
        """
        state_enum = sts.lookup(state.title(), field="name")
        if state_enum is None:
            logger.error("Could not find state")
            return False
        state_fips = state_enum.fips

        my_csv_json = None
        cache_file_rel_path = f"{os.path.dirname(__file__)}{os.sep}.cache{os.sep}{year}-acs-table-{table}-for-state-{state_fips}.json"

        if os.path.exists(cache_file_rel_path):
            with open(cache_file_rel_path, "r") as f:
                logger.debug(f"cache for {cache_file_rel_path} being read.")
                my_csv_json = json.load(f)
        else:
            # has to be 2019
            url = f"https://api.census.gov/data/{year}/acs/acs5/profile?get=group({table})&for=zip%20code%20tabulation%20area:*&in=state:{state_fips}"
            req = self.get(url)
            if req is None:
                logger.info(f"{req = }")
                return False
            my_csv_json = req.json()
            with open(cache_file_rel_path, "w") as f:
                json.dump(my_csv_json, f)

        if my_csv_json is None:
            logger.info(f"{my_csv_json = }")
            return False
        # list of lists, where header is first list
        self.translate_unique_groups_to_labels_for_header_list(
            my_csv_json[0], table, year
        )
        df = pl.DataFrame(my_csv_json, orient="row")
        df = (
            df.rename(df.head(1).to_dicts().pop())
            .slice(1)  # type: ignore
            .drop("NAME", cs.matches("[Aa]nnotation"), cs.matches(f"{table}.*A\b"))
            .rename({"zip code tabulation area": "ZCTA", "state": "STATE_FIPS"})
            # might wanna make these schema overrides
            .cast(
                {
                    cs.matches("!!"): pl.Float32,
                    "STATE_FIPS": pl.Int32,
                    "ZCTA": pl.Int32,
                }
            )
        )
        parent_path = pathlib.Path(os.path.dirname(__file__)).parent.parent
        df.write_csv(
            f"{parent_path}{os.sep}output{os.sep}acs5-group-{table}-zcta-state-{state_fips}.csv"
        )
        # return df
        return True


if __name__ == "__main__":
    r = CensusAPI()
    # path = pathlib.Path(os.path.dirname(__file__)).parent.parent / "output"
    # print(path)
    print(r.get_table_group_for_zcta_by_state_by_year("DP05", "2019", "california"))
    # print(r.get_table_row_label("DP05_0064PE", "2019"))
