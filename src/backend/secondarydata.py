import datetime
import json
import os
from pathlib import Path
import re
from enum import Enum, StrEnum
from typing import Any

import polars as pl
import polars.selectors as cs
import requests
from backend.helper import log, req_get_wrapper
from backend.us import states as sts
from dotenv import load_dotenv


load_dotenv()

CENSUS_DATA_DIR_PATH = Path(__file__).parent.parent.parent / "output" / "census_data"
CENSUS_DATA_CACHE_PATH = CENSUS_DATA_DIR_PATH / "cache"

# https://www.dcf.ks.gov/services/PPS/Documents/PPM_Forms/Section_5000_Forms/PPS5460_Instr.pdf
replace_dict = {
    "PercentMarginOfError": "PME",
    "Estimate": "EST",
    "Percent": "PCT",
    "MarginOfError": "MOE",
    "AnnotationOf": "ann",
    "AmericanIndianAndAlaskaNative": "_A_",
    "AmericanIndianOrAlaskaNative": "_A_",
    "BlackOrAfricanAmerican": "_B_",
    "PacificIslanderIncludingNativeHawaiian": "_P_",
    "NativeHawaiianAndOtherPacificIslander": "_P_",
    "Asian": "_S_",
    "White": "_W_",
    "Unknown": "_O_",
    "SomeOtherRace": "_O_",
    "(?<!Not)HispanicOrLatino": "_H_",
    "NotHispanicOrLatino": "_N_",
    "TotalPopulation": "TPOP",
    "OrMore": "plus",
    "AndOver": "plus",
    "One": "1",
    "Two": "2",
    "Three": "3",
}


class EIADataRetriever:
    """Interact with the EIA open data API.

    Note:
        This is the "manual" for this API:
        https://www.eia.gov/opendata/pdf/EIA-APIv2-HandsOn-Webinar-11-Jan-23.pdf
    """

    HEATING_OIL_STATES_ABBR = {
        sts.CT.abbr,
        sts.DC.abbr,
        sts.DE.abbr,
        sts.IA.abbr,
        sts.IL.abbr,
        sts.IN.abbr,
        sts.KS.abbr,
        sts.KY.abbr,
        sts.MA.abbr,
        sts.MD.abbr,
        sts.ME.abbr,
        sts.MI.abbr,
        sts.MN.abbr,
        sts.MO.abbr,
        sts.NC.abbr,
        sts.ND.abbr,
        sts.NE.abbr,
        sts.NH.abbr,
        sts.NJ.abbr,
        sts.NY.abbr,
        sts.OH.abbr,
        sts.PA.abbr,
        sts.RI.abbr,
        sts.SD.abbr,
        sts.VA.abbr,
        sts.VT.abbr,
        sts.WI.abbr,
    }

    PROPANE_STATES_ABBR = {
        sts.AL.abbr,
        sts.AR.abbr,
        sts.CO.abbr,
        sts.CT.abbr,
        sts.DE.abbr,
        sts.FL.abbr,
        sts.GA.abbr,
        sts.IL.abbr,
        sts.IN.abbr,
        sts.KS.abbr,
        sts.KY.abbr,
        sts.KY.abbr,
        sts.MA.abbr,
        sts.MD.abbr,
        sts.ME.abbr,
        sts.MI.abbr,
        sts.MN.abbr,
        sts.MO.abbr,
        sts.MS.abbr,
        sts.MT.abbr,
        sts.NC.abbr,
        sts.ND.abbr,
        sts.NE.abbr,
        sts.NH.abbr,
        sts.NJ.abbr,
        sts.NY.abbr,
        sts.OH.abbr,
        sts.OK.abbr,
        sts.PA.abbr,
        sts.RI.abbr,
        sts.SD.abbr,
        sts.TN.abbr,
        sts.TX.abbr,
        sts.UT.abbr,
        sts.VA.abbr,
        sts.VT.abbr,
        sts.WI.abbr,
    }

    class HeaterEfficiencies(Enum):
        """Combination of system efficiency and distribution efficiency.

        Note:
            Numbers taken from https://www.efficiencymaine.com/at-home/heating-cost-comparison/
        """

        HEAT_PUMP_GEOTHERMAL = 3.69
        HEAT_PUMP_DUCTLESS = 2.7  # mini split
        HEAT_PUMP_DUCTED = 2.16
        BASEBOARD = 1
        KEROSENE_ROOM_HEATER = 0.87
        PROPANE_BOILER = 0.837
        NG_BOILER = 0.828
        NG_ROOM_HEATER = 0.81
        PROPANE_ROOM_HEATER = 0.81
        OIL_BOILER = 0.783
        WOOD_STOVE = 0.75
        PELLET_STOVE = 0.75
        NG_FURNACE = 0.744  #! double check this value
        PROPANE_FURNACE = 0.744
        OIL_FURNACE = 0.704
        PELLET_BOILER = 0.639

    class EnergyType(Enum):
        PROPANE = 1
        HEATING_OIL = 2
        NATURAL_GAS = 3
        ELECTRICITY = 4

    class PetroleumProductTypes(StrEnum):
        NATURAL_GAS = "EPG0"
        PROPANE = "EPLLPA"
        HEATING_OIL = "EPD2F"

    class FuelBTUConversion(Enum):
        # https://www.edf.org/sites/default/files/10071_EDF_BottomBarrel_Ch3.pdf
        # https://www.eia.gov/energyexplained/units-and-calculators/british-thermal-units.php
        # https://www.eia.gov/energyexplained/units-and-calculators/
        NO1_OIL_BTU_PER_GAL = 135_000
        NO2_OIL_BTU_PER_GAL = 140_000
        NO4_OIL_BTU_PER_GAL = 146_000
        NO5_OIL_BTU_PER_GAL = 144_500
        NO6_OIL_BTU_PER_GAL = 150_000
        HEATING_OIL_BTU_PER_GAL = 138_500
        ELECTRICITY_BTU_PER_KWH = 3_412.14
        NG_BTU_PER_MCT = 1_036_000  # 1000 cubic feet of gas
        NG_BTU_PER_THERM = 100_000
        PROPANE_BTU_PER_GAL = 91_452
        WOOD_BTU_PER_CORD = 20_000_000

    def __init__(self):
        self.eia_base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")
        if self.api_key is None:
            log(
                "No Census API key found in a .env file in project directory. please request a key at https://www.eia.gov/opendata/register.php",
                "critical",
            )
            exit()

    def price_per_mbtu_with_efficiency(
        self, energy_price_dict: dict
    ) -> dict[str, str | EnergyType | float]:
        """Convert an energy source's price per quantity into price per BTU with an efficiency.

        Note:
            Efficiency data taken from https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf

        See also:
            `EIADataRetriever.HeaterEfficiencies`

        Args:
            energy_price_dict (dict): energy source json

        Returns:
            dict: new dictionary with btu centric pricing
        """
        #! make new function based on burner type/ end usage type
        CENTS_IN_DOLLAR = 100
        match energy_price_dict.get("type"):
            case self.EnergyType.PROPANE.value:
                # for loop is done for every case since i dont want to use `eval` or parse a string of division to keep PEMDAS. this is why i dont have an efficiency func yet
                for key, value in energy_price_dict.items():
                    if (
                        key in ["type", "state", None]
                        or energy_price_dict.get(key) is None
                    ):
                        continue
                    energy_price_dict[key] = (
                        value
                        / (
                            self.FuelBTUConversion.PROPANE_BTU_PER_GAL.value
                            * self.HeaterEfficiencies.PROPANE_FURNACE.value
                        )
                        * 1_000
                    )
            case self.EnergyType.NATURAL_GAS.value:
                for key, value in energy_price_dict.items():
                    if (
                        key in ["type", "state", None]
                        or energy_price_dict.get(key) is None
                    ):
                        continue
                    energy_price_dict[key] = (
                        value
                        / (
                            self.FuelBTUConversion.NG_BTU_PER_MCT.value
                            * self.HeaterEfficiencies.NG_FURNACE.value
                        )
                        * 1_000
                    )
            case self.EnergyType.ELECTRICITY.value:
                for key, value in energy_price_dict.items():
                    if (
                        key in ["type", "state", None]
                        or energy_price_dict.get(key) is None
                    ):
                        continue
                    energy_price_dict[key] = (
                        value
                        / CENTS_IN_DOLLAR
                        / (
                            self.FuelBTUConversion.ELECTRICITY_BTU_PER_KWH.value
                            * self.HeaterEfficiencies.HEAT_PUMP_DUCTED.value
                        )
                        * 1_000
                    )
            case self.EnergyType.HEATING_OIL.value:
                for key, value in energy_price_dict.items():
                    if (
                        key in ["type", "state", None]
                        or energy_price_dict.get(key) is None
                    ):
                        continue
                    energy_price_dict[key] = (
                        value
                        / (
                            self.FuelBTUConversion.HEATING_OIL_BTU_PER_GAL.value
                            * self.HeaterEfficiencies.OIL_BOILER.value
                        )
                        * 1_000
                    )
            case _:
                log("Could not translate dict to btu per price.", "warn")

        return energy_price_dict

    # api to dict handler Helpers
    def price_dict_to_clean_dict(
        self, eia_json: dict, energy_type: EnergyType, state: str
    ) -> dict[str, str | EnergyType | float]:
        """Clean JSON data returned by EIA's API.

        Args:
            eia_json (dict): the response JSON
            energy_type (EnergyType): the energy type
            state (str): the state

        Returns:
            dict[str, str | EnergyType | float]: cleaned JSON
        """
        # price key is different for electricity
        accessor = "value"
        if "product" not in eia_json["response"]["data"][0]:
            accessor = "price"

        result_dict = {
            entry["period"]: entry[f"{accessor}"]
            for entry in eia_json["response"]["data"]
        }
        result_dict["type"] = energy_type.value
        result_dict["state"] = state

        return result_dict

    def price_df_to_clean_dict(
        self, eia_df: pl.DataFrame, energy_type: EnergyType, state: str
    ) -> dict[str, str | EnergyType | float]:
        """Clean DataFrame data consisting of EIA API data.

        Args:
            eia_df (pl.DataFrame): the DataFrame to clean
            energy_type (EnergyType): the energy type
            state (str): the state

        Returns:
            dict[str, str|EnergyType|float]: the dict
        """
        result_dict = {}
        for row in eia_df.rows(named=True):
            year_month = f"{row.get("year")}-{row.get("month"):02}"
            if row.get("monthly_avg_price") is not None:
                result_dict[year_month] = round(row.get("monthly_avg_price"), 3)  # type: ignore
        result_dict["type"] = energy_type.value
        result_dict["state"] = state
        return result_dict

    # api to dict handler
    def price_to_clean_dict(
        self, price_struct: dict | pl.DataFrame, energy_type: EnergyType, state: str
    ) -> dict[str, str | EnergyType | float]:
        """Handle the different data types that EIA data could be stored in.

        Args:
            price_struct (dict | pl.DataFrame): a data structure containing the year, month, and price info
            energy_type (EnergyType): the energy type
            state (str): the state

        Raises:
            TypeError: raised if the type of `price_struct` is not supported

        Returns:
            dict[str, str|EnergyType|float]: the normalized and structured data in dict form
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
        """Get a state's average monthly energy price.

        Note:
            Data is returned in cents/KWh.

        Args:
            state (str): the 2 character postal code of a state
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: the dictionary in `year-month: price` form
        """
        url = f"{self.eia_base_url}/electricity/retail-sales/data/?frequency=monthly&data[0]=price&facets[stateid][]={state}&facets[sectorid][]=RES&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = req_get_wrapper(url)
        eia_request.raise_for_status()

        return eia_request.json()

    def monthly_ng_price_per_mcf(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict[str, Any]:
        """Get a state's average natural gas price.

        Note:
            Data is returned in dollars per mega cubic feet.

        Args:
            state (str): the 2 character postal code of a state
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # $/mcf
        url = f"https://api.eia.gov/v2/natural-gas/pri/sum/data/?frequency=monthly&data[0]=value&facets[duoarea][]=S{state}&facets[process][]=PRS&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = req_get_wrapper(url)
        eia_request.raise_for_status()

        return eia_request.json()

    def monthly_heating_season_heating_oil_price_per_gal(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> pl.DataFrame:
        """Get a state's average heating oil price.

        Note:
            Data returned is in dollars per gallon.

            Only these states are tracked, and only for the months October through March:
                * CT
                * DC
                * DE
                * IA
                * IL
                * IN
                * KS
                * KY
                * MA
                * MD
                * ME
                * MI
                * MN
                * MO
                * NC
                * ND
                * NE
                * NH
                * NJ
                * NY
                * OH
                * PA
                * RI
                * SD
                * VA
                * VT
                * WI
        Args:
            state (str): 2 char postal code
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=weekly&data[0]=value&facets[duoarea][]=S{state}&facets[product][]=EPD2F&start={start_date}&end={end_date}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = req_get_wrapper(url)
        eia_request.raise_for_status()

        json = eia_request.json()
        df = pl.DataFrame(json["response"]["data"])
        # becomes int, so months are sig figs
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
        """Get a state's average propane price in dollars per gal.

        Note:
            Only these states are tracked, and only for the months October through Marc:
                * AL
                * AR
                * CO
                * CT
                * DE
                * FL
                * GA
                * IL
                * IN
                * KS
                * KY
                * KY
                * MA
                * MD
                * ME
                * MI
                * MN
                * MO
                * MS
                * MT
                * NC
                * ND
                * NE
                * NH
                * NJ
                * NY
                * OH
                * OK
                * PA
                * RI
                * SD
                * TN
                * TX
                * UT
                * VA
                * VT
                * WI

        Args:
            state (str): 2 character postal code
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=weekly&data[0]=value&facets[process][]=PRS&facets[duoarea][]=S{state}&facets[product][]=EPLLPA&start={start_date}&end={end_date}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = req_get_wrapper(url)
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

    def monthly_price_per_mbtu_by_energy_type(
        self,
        energy_type: EnergyType,
        state: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[str, str | EnergyType | float]:
        """Get the cost per MBTU for the given energy type for the state, over the given period of time. Refer to EIA's documentation
        for changes to data collection during certain years.

        Args:
            energy_type (EnergyType): The energy type
            state (str): the 2 character postal abbreviation. Note that for heating oil, only certain states have this information collected
            start_date (datetime.date): the date for which to start the search. Inclusive. Not that for heating oil, only heating months will be returned
            end_date (datetime.date): the date for which to end the search. Non inclusive

        Raises:
            NotImplementedError: Invalid energy type

        Returns:
            dict: year-month: price in USD to BTU
        """
        if len(state) > 2:
            state = sts.lookup(state).abbr  # type: ignore
        match energy_type:
            case self.EnergyType.PROPANE:
                return self.price_per_mbtu_with_efficiency(
                    self.price_to_clean_dict(
                        self.monthly_heating_season_propane_price_per_gal(
                            state, start_date, end_date
                        ),
                        energy_type,
                        state,
                    )
                )
            case self.EnergyType.NATURAL_GAS:
                return self.price_per_mbtu_with_efficiency(
                    self.price_to_clean_dict(
                        self.monthly_ng_price_per_mcf(state, start_date, end_date),
                        energy_type,
                        state,
                    )
                )
            case self.EnergyType.ELECTRICITY:
                return self.price_per_mbtu_with_efficiency(
                    self.price_to_clean_dict(
                        self.monthly_electricity_price_per_kwh(
                            state, start_date, end_date
                        ),
                        energy_type,
                        state,
                    )
                )
            case self.EnergyType.HEATING_OIL:
                return self.price_per_mbtu_with_efficiency(
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

    def monthly_price_per_mbtu_by_energy_type_by_state(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> list[Any]:
        """Get all available energy prices per MBTU, taking efficiency into account, for a state.

        Note:
            Please keep times to within a year. For the non oil and propane, you have to go a month past.

        Args:
            state (str): 2 character postal code
            start_date (datetime.date): start date
            end_date (datetime.date): end date

        Returns:
            list[Any]: list of price dicts for available energy types for a state
        """
        if len(state) > 2:
            state = sts.lookup(state).abbr  # type: ignore

        dicts_to_return = []
        if state in self.HEATING_OIL_STATES_ABBR:
            dicts_to_return.append(
                self.monthly_price_per_mbtu_by_energy_type(
                    self.EnergyType.HEATING_OIL, state, start_date, end_date
                )
            )
        if state in self.PROPANE_STATES_ABBR:
            dicts_to_return.append(
                self.monthly_price_per_mbtu_by_energy_type(
                    self.EnergyType.PROPANE, state, start_date, end_date
                )
            )
        dicts_to_return.append(
            self.monthly_price_per_mbtu_by_energy_type(
                self.EnergyType.NATURAL_GAS, state, start_date, end_date
            )
        )
        dicts_to_return.append(
            self.monthly_price_per_mbtu_by_energy_type(
                self.EnergyType.ELECTRICITY, state, start_date, end_date
            )
        )
        log(f"{dicts_to_return = }", "debug")
        return dicts_to_return


class CensusDataRetriever:
    """Interact with the Census data API.

    Note:
        ACS5 paths can be found here: https://api.census.gov/data/2019/acs/acs5.html"""

    def __init__(self) -> None:
        self.base_url = "https://data.census.gov/"
        # https://api.census.gov/data/2021/acs/acs5/profile/variables.html
        self.api_key = os.getenv("CENSUS_API_KEY")
        if self.api_key is None:
            log(
                "No Census API key found in a .env file in project directory. please request a key at https://api.census.gov/data/key_signup.html",
                "critical",
            )
            exit()
        self.MAX_COL_NAME_LENGTH = 80

    def _get(self, url: str) -> requests.Response | None:
        r = requests.get(url, timeout=65)
        if r.status_code == 400:
            log(f"Unknown variable {r.text.split("variable ")[-1]}", "info")
            return None
        return r

    def get_and_cache_data(
        self, file_name: str, url_to_lookup_on_miss: str
    ) -> dict[str, str] | bool:
        """Cache files.

        Args:
            file_name (str): file name to save/lookup
            url_to_lookup_on_miss (str): the Census url to lookup

        Returns:
            bool | dict[str, str] | None | Any: the dict of `tablename: label` or
        """
        CENSUS_DATA_CACHE_PATH.mkdir(parents=True, exist_ok=True)

        my_json = None

        try:
            with open(CENSUS_DATA_CACHE_PATH / file_name, mode="r") as f:
                log(f"Reading {file_name}", "debug")
                try:
                    my_json = json.load(f)
                except json.JSONDecodeError:
                    log("Could not decode cached census file", "error")
                    return False
        except FileNotFoundError:
            req = self._get(url_to_lookup_on_miss)
            log(f"Getting {url_to_lookup_on_miss}...", "info")
            if req is None:
                log(f"Could not get census file {file_name}.", "error")
                return False
            req.raise_for_status()
            my_json = req.json()
            with open(CENSUS_DATA_CACHE_PATH / file_name, "w") as f:
                json.dump(my_json, f)

        return my_json

    def get_race_makeup_by_zcta(self, zcta: str) -> str | None:
        """Get race make up by zcta from. DO NOT USE

        Note:
            use `get_table_group_for_zcta_by_state_by_year`

        Args:
            zcta (str): zcta

        Returns:
            str | None: text or none
        """
        # get white, black, american indian/native alaskan, asian, NH/PI, other. note that these are estimates, margin of error can be had with "M"
        req = self._get(
            f"https://api.census.gov/data/2021/acs/acs5/profile?get=DP05_0064E,DP05_0065E,DP05_0066E,DP05_0067E,DP05_0068E,DP05_0069E&for=zip%20code%20tabulation%20area:{zcta}&key={self.api_key}"
        )
        if req is None:
            return None
        return req.text

    def _get_acs5_profile_table_to_group_name(
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
        file_name = f"{year}-acs5-profile-groups-{table}.json"
        groups_url = (
            f"https://api.census.gov/data/{year}/acs/acs5/profile/groups/{table}.json"
        )
        groups_to_label_translation = self.get_and_cache_data(file_name, groups_url)
        if groups_to_label_translation is False:
            log("Something is wrong with groups label dict", "warn")
            return None
        return groups_to_label_translation["variables"]  # type: ignore

    def _translate_and_truncate_unique_acs5_profile_groups_to_labels_for_header_list(
        self, headers: list[str], table: str, year: str
    ) -> None:
        """Get the label name for a table and row for the acs5 profile surveys.

        Args:
            headers (list[str]): header row
            table (str): have to look again
            year (str): the year

        Returns:
            None: translates the list of table_row_selector to its english label
        """
        # is going to read the file multiple times, save last req as {"table": req_json[table]...} for this?
        groups_to_label_translation_dict = self._get_acs5_profile_table_to_group_name(
            table, year
        )
        if groups_to_label_translation_dict is None:
            log("Could not translate headers", "warn")
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

    def generate_acs5_profile_table_group_for_zcta_by_year(
        self, table: str, year: str
    ) -> str:
        """CSV output of an acs 5 year profile survey table.

        TODO:
            Update func name

        Args:
            table (str): census demo acs5 table
            year (str): year to search

        Returns:
            str: file path where output is saved
        """
        file_name = f"{year}-acs-profile-table-{table}.json"
        url = f"https://api.census.gov/data/{year}/acs/acs5/profile?get=group({table})&for=zip%20code%20tabulation%20area:*"
        list_of_list_table_json = self.get_and_cache_data(file_name, url)

        if list_of_list_table_json is False:
            log(
                f"Could not load table {table}. Perhaps the api is down or there was an error saving/reading the file.",
                "warn",
            )
            return ""

        self._translate_and_truncate_unique_acs5_profile_groups_to_labels_for_header_list(
            list_of_list_table_json[0],  # type: ignore
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
        table_file_name = CENSUS_DATA_DIR_PATH / f"acs5-profile-group-{table}-zcta.csv"
        df.write_csv(table_file_name)
        return str(table_file_name)

    def _get_acs5_subject_table_to_group_name(
        self, table: str, year: str
    ) -> dict[str, Any] | None:
        """Get a JSON representation of a table's attributes.

        Note:
            Tables can be found at: https://www.census.gov/acs/www/data/data-tables-and-tools/subject-tables/

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
            str | Any: variables
        """
        file_name = f"{year}-acs5-subject-groups-{table}.json"
        groups_url = (
            f"https://api.census.gov/data/{year}/acs/acs5/subject/groups/{table}.json"
        )
        groups_to_label_translation = self.get_and_cache_data(file_name, groups_url)
        if groups_to_label_translation is False:
            log("Something is wrong with groups label dict", "warn")
            return None
        return groups_to_label_translation["variables"]  # type: ignore

    def _translate_and_truncate_unique_acs5_subject_groups_to_labels_for_header_list(
        self, headers: list[str], table: str, year: str
    ) -> None:
        """Gets the label name for a table and row for the acs5 profile surveys.

        Args:
            headers (list[str]): headers
            table (str): table
            year (str): year
        """
        # is going to read the file multiple times, save last req as {"table": req_json[table]...} for this?
        groups_to_label_translation_dict = self._get_acs5_subject_table_to_group_name(
            table, year
        )
        if groups_to_label_translation_dict is None:
            log("Could not translate headers", "warn")
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

    def generate_acs5_subject_table_group_for_zcta_by_year(
        self, table: str, year: str
    ) -> str:
        """CSV output of a acs 5 year subject survey table

        Args:
            table (str): census acs5 table
            year (str): year to search
        """
        file_name = f"{year}-acs-subject-table-{table}.json"
        url = f"https://api.census.gov/data/{year}/acs/acs5/subject?get=group({table})&for=zip%20code%20tabulation%20area:*"
        list_of_list_table_json = self.get_and_cache_data(file_name, url)
        if list_of_list_table_json is False:
            log(
                f"Could not load table {table}. Perhaps the api is down or there was an error saving/reading the file.",
                "warn",
            )
            return ""

        self._translate_and_truncate_unique_acs5_subject_groups_to_labels_for_header_list(
            list_of_list_table_json[0],  # type: ignore
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
        table_file_name = CENSUS_DATA_DIR_PATH / f"acs5-subject-group-{table}-zcta.csv"
        # may not have to write. but cache func doesn't return whether it hits or not
        df.write_csv(table_file_name)
        return str(table_file_name)
