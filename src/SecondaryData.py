import datetime
import os
from enum import Enum, StrEnum
from typing import Any

import Helper as Helper
import polars as pl
import requests
from dotenv import load_dotenv

load_dotenv()


class EIADataRetriever:
    # Electricity:
    #   can get by month per state
    # Propane and Heating oil:
    #   *per month is per heating month*
    #   can get by month per PAD, or by us average
    #   can get by week per tracked state
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

    def get(self, url: str) -> str | Any:
        r = requests.get(url, timeout=15)
        if r.status_code == 400:
            return f"Unknown variable {r.text.split("variable ")[-1]}"
        return r.text
        

    def get_race_makeup_by_zcta(self, zcta: str):
        #get white, black, american indian/native alaskan, asian, NH/PI, other. note that these are estimates, margin of error can be had with "M"
        return self.get(f"https://api.census.gov/data/2021/acs/acs5/profile?get=DP05_0064E,DP05_0065E,DP05_0066E,DP05_0067E,DP05_0068E,DP05_0069E&for=zip%20code%20tabulation%20area:{zcta}&key={self.api_key}")


if __name__ == "__main__":
    print(CensusAPI().get_race_makeup_by_zcta("90715"))
