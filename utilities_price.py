from dotenv import load_dotenv
import os
import requests
import helper
import datetime
import polars as pl
from enum import Enum, StrEnum

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
        NO1_OIL_BTU_PER_GAL = 135000,
        NO2_OIL_BTU_PER_GAL = 140000,
        NO4_OIL_BTU_PER_GAL = 146000,
        NO5_OIL_BTU_PER_GAL = 144500,
        NO6_OIL_BTU_PER_GAL = 150000,
        HEATING_OIL_BTU_PER_GAL = 138500,
        ELECTRICITY_BTU_PER_KWH = 3412.14,
        #1000 cubic feet
        NG_BTU_PER_MCT = 1036,
        NG_BTU_PER_THERM = 100000,
        PROPANE_BTU_PER_GAL = 91452,
        WOOD_BTU_PER_CORD = 20000000, 
        
    def __init__(self):
        self.eia_base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")

    # normalize prices
    def _price_per_btu_converter(self, energy_price_dict: dict) -> dict:
        """Converts energy source's price per quantity to price per BTU.

        Args:
            energy_source (_type_): energy source json

        Returns:
            dict: new dictionary with btu centric pricing
        """
        # https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf
        # Natural gas: $13.86 per thousand cubic feet /1.036 million Btu per thousand cubic feet = $13.38 per million Btu
        #! currently doesn't take into account efficiency  
        btu_dict = {}
        factor = 1
        match energy_price_dict.get(type):
            case self.EnergyTypes.PROPANE:
                factor = self.FuelBTUConversion.PROPANE_BTU_PER_GAL # *efficiency
            case self.EnergyTypes.NATURAL_GAS:
                factor = self.FuelBTUConversion.NG_BTU_PER_MCT # *efficiency
            case self.EnergyTypes.ELECTRICITY:
                factor = self.FuelBTUConversion.ELECTRICITY_BTU_PER_KWH # *efficiency
            case self.EnergyTypes.HEATING_OIL:
                factor = self.FuelBTUConversion.HEATING_OIL_BTU_PER_GAL # *efficiency
                
        for key, value in energy_price_dict.items():
            if key in ["type", "state"]:
                btu_dict[key] = value
                continue
            btu_dict[key] = value / factor
            
        return btu_dict

    # api to dict handler helpers
    def _price_dict_to_clean_dict(self, eia_json: dict, energy_type: EnergyTypes, state: str) -> dict[str:float]:
        """Cleaner for raw json data returned by EIA's API.

        Args:
            eia_json (_type_): the dirty json

        Returns:
            dict: cleaned json with state and energy type
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

    def _price_df_to_clean_dict(self, eia_df: pl.DataFrame, energy_type: EnergyTypes, state: str) -> dict[str:float]:
        result_dict = {}
        for row in eia_df.rows(named=True):
            year_month = f"{row.get("year")}-{row.get("month")}"
            result_dict[year_month] = round(row.get("monthly_avg_price"),3)
        result_dict["type"] = energy_type    
        result_dict["state"] = state
        return result_dict
  
    # api to dict handler
    def _price_to_clean_dict(self, price_struct: dict|pl.DataFrame, energy_type: EnergyTypes, state: str)-> dict[str:float]:
        match price_struct:
            case dict():
                return self.price_dict_to_clean_dict(price_struct, energy_type, state)
            case pl.DataFrame():
                return self.price_df_to_clean_dict(price_struct, energy_type, state)
            case _:
                raise TypeError(f"Type not supported: {type(energy_type)}")
    
    # api interaction                          
    def _monthly_electricity_price_per_kwh(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        """Returns a dictionary for a given state's monthly energy price. Price is in cents per KWh

        Args:
            state (str): the 2 character postal code of a state
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: the dictionary in year-month: price form
        """
        # cent/ kwh
        url = f"{self.eia_base_url}/electricity/retail-sales/data?data[]=price&facets[sectorid][]=RES&facets[stateid][]={state}&frequency=monthly&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = helper.req_get_wrapper(url)
        eia_request.raise_for_status()

        return eia_request.json()                        

    def _monthly_ng_price_per_mcf(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        """Returns a dictionary of year-month to price of a given state's price per thousand cubic feet.

        Args:
            state (str): the 2 character postal code of a state
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        url = f"https://api.eia.gov/v2/natural-gas/pri/sum/data/?frequency=monthly&data[0]=value&facets[duoarea][]=S{state}&facets[process][]=PRS&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = helper.req_get_wrapper(url)
        eia_request.raise_for_status()
        
        return eia_request.json()
    
    def _monthly_heating_season_heating_oil_price_per_gal(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> pl.DataFrame:
        """Returns a dictionary of year-month to price of a united states average price per gallon.

        Args:
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=weekly&data[0]=value&facets[duoarea][]=S{state}&facets[product][]=EPD2F&start={start_date}&end={end_date}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = helper.req_get_wrapper(url)
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
        """Returns a dictionary of year-month to price of a united states average price per gallon.

        Args:
            start_date (datetime.date): the start date, inclusive
            end_date (datetime.date): the end date, non inclusive

        Returns:
            dict: _description_
        """
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=weekly&data[0]=value&facets[duoarea][]=S{state}&facets[product][]=EPLLPA&start={start_date}&end={end_date}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = helper.req_get_wrapper(url)
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

    def monthly_price_per_btu_by_energy_type(self, energy_type: EnergyTypes, state: str, start_date: datetime.date, end_date: datetime.date) -> dict[str:float]:
        """Returns an energy type's cost per btu for a given state.

        Raises:
            NotImplementedError: Raised if the energy type does not exist

        Returns:
            dict: Returns a dictionary containing the state, the energy type, and price per btu by month over the given time period
        """
        match energy_type:
            case self.EnergyTypes.PROPANE:                
                return self.price_per_btu_converter(self.price_to_clean_dict(self.monthly_heating_season_propane_price_per_gal(state, start_date, end_date), energy_type, state))
            case self.EnergyTypes.NATURAL_GAS:
                return self.price_per_btu_converter(self.price_to_clean_dict(self.monthly_ng_price_per_mcf(state, start_date, end_date), energy_type, state))
            case self.EnergyTypes.ELECTRICITY:
                return self.price_per_btu_converter(self.price_to_clean_dict(self.monthly_electricity_price_per_kwh(state, start_date, end_date), energy_type, state))
            case self.EnergyTypes.HEATING_OIL:
                return self.price_per_btu_converter(self.price_to_clean_dict(self.monthly_heating_season_heating_oil_price_per_gal(state, start_date, end_date), energy_type, state))         
            case _:
                raise NotImplementedError(f'Unsupported energy type: {energy_type}')


if __name__ == "__main__":
    data_retriever = EIADataRetriever()
    
    elec = data_retriever.monthly_price_per_btu_by_energy_type(data_retriever.EnergyTypes.ELECTRICITY, "NY", datetime.date(2022, 1, 1), datetime.date(2023, 1, 1))
    prop = data_retriever.monthly_price_per_btu_by_energy_type(data_retriever.EnergyTypes.PROPANE, "NY", datetime.date(2022, 1, 1), datetime.date(2023, 1, 1))
    oil = data_retriever.monthly_price_per_btu_by_energy_type(data_retriever.EnergyTypes.HEATING_OIL, "NY", datetime.date(2022, 1, 1), datetime.date(2023, 1, 1))
    ng = data_retriever.monthly_price_per_btu_by_energy_type(data_retriever.EnergyTypes.NATURAL_GAS, "NY", datetime.date(2022, 1, 1), datetime.date(2023, 1, 1))

    print(
        f"electricity: {elec}\nheating oil: {oil}\npropane: {prop}\nnatural gas: {ng}"
    )
