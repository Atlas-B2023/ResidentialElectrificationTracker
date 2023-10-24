from dotenv import load_dotenv
import os
import requests
import datetime

load_dotenv()


class EIADataRetriever:
    # Electricity:
    #   can get by month per state
    # Propane and Heating oil:
    #   *per month is per heating month*
    #   can get by month per PAD, or by us average
    #   can get by week per tracked state
    def __init__(self):
        self.eia_base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")
        # https://www.edf.org/sites/default/files/10071_EDF_BottomBarrel_Ch3.pdf
        # https://www.eia.gov/energyexplained/units-and-calculators/british-thermal-units.php
        # https://www.eia.gov/energyexplained/units-and-calculators/
        self.NO1_OIL_BTU_PER_GAL = 135000
        self.NO2_OIL_BTU_PER_GAL = 140000
        self.NO4_OIL_BTU_PER_GAL = 146000
        self.NO5_OIL_BTU_PER_GAL = 144500
        self.NO6_OIL_BTU_PER_GAL = 150000
        self.HEATING_OIL_BTU_PER_GAL = 138500
        self.ELECTRICITY_BTU_PER_KWH = 3412.14
        self.NG_BTU_PER_CUFT = 1036
        self.NG_BTU_PER_THERM = 100000
        self.PROPANE_BTU_PER_GAL = 91452
        self.WOOD_BTU_PER_CORD = 20000000

    def energy_source_price_per_btu(self, energy_source) -> float:
        # https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf
        # Natural gas: $13.86 per thousand cubic feet /1.036 million Btu per thousand cubic feet = $13.38 per million Btu
        return 1

    def price_json_to_dict(self, eia_json) -> dict:
        if (
            eia_json is None
            or "response" not in eia_json
            or "data" not in eia_json["response"]
        ):
            return {}
        if "product" not in eia_json["response"]["data"][0]:
            # electricity
            return {
                entry["period"]: entry["price"]
                for entry in eia_json["response"]["data"]
            }
        if eia_json["response"]["data"][0]["product"] == "EPD2F" or "EPLLPA" or "EPG0":
            # heating oil, propane, and natural gas
            return {
                entry["period"]: entry["value"]
                for entry in eia_json["response"]["data"]
            }

    def monthly_energy_price_per_kwh(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        # cent/ kwh
        url = f"{self.eia_base_url}/electricity/retail-sales/data?data[]=price&facets[sectorid][]=RES&facets[stateid][]={state}&frequency=monthly&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = requests.get(url)
        if eia_request.status_code == 200:
            return self.price_json_to_dict(eia_request.json())
        else:
            return {}

    def monthly_heating_season_heating_oil_price_per_gal(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=monthly&data[0]=value&facets[series][]=M_EPD2F_PRS_NUS_DPG&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&sort[1][column]=series&sort[1][direction]=asc&api_key={self.api_key}"

        eia_request = requests.get(url)
        if eia_request.status_code == 200:
            return self.price_json_to_dict(eia_request.json())
        else:
            return {}

    def monthly_heating_season_propane_price_per_gal(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        # heating season is Oct - march, $/gal
        url = f"https://api.eia.gov/v2/petroleum/pri/wfr/data/?frequency=monthly&data[0]=value&facets[series][]=M_EPLLPA_PRS_NUS_DPG&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&sort[1][column]=series&sort[1][direction]=asc&api_key={self.api_key}"

        eia_request = requests.get(url)
        if eia_request.status_code == 200:
            return self.price_json_to_dict(eia_request.json())
        else:
            return {}

    def monthly_ng_price_per_mcf(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        url = f"https://api.eia.gov/v2/natural-gas/pri/sum/data/?frequency=monthly&data[0]=value&facets[duoarea][]=S{state}&facets[process][]=PRS&start={start_date.year}-{start_date.month:02}&end={end_date.year}-{end_date.month:02}&sort[0][column]=period&sort[0][direction]=asc&api_key={self.api_key}"

        eia_request = requests.get(url)
        if eia_request.status_code == 200:
            return self.price_json_to_dict(eia_request.json())
        else:
            return {}


if __name__ == "__main__":
    data_retriever = EIADataRetriever()
    result = data_retriever.monthly_energy_price_per_kwh(
        "CO", datetime.date(2022, 1, 1), datetime.date(2022, 12, 1)
    )
    result2 = data_retriever.monthly_heating_season_heating_oil_price_per_gal(
        datetime.date(2022, 1, 1), datetime.date(2023, 1, 1)
    )
    result3 = data_retriever.monthly_heating_season_propane_price_per_gal(
        datetime.date(2022, 1, 1), datetime.date(2023, 1, 1)
    )
    result4 = data_retriever.monthly_ng_price_per_mcf(
        "CO", datetime.date(2022, 1, 1), datetime.date(2023, 1, 1)
    )
    print(f"electricity: {result}\nheating oil: {result2}\n propane: {result3}\n natural gas: {result4}")
    # print(f"ng: {result4}")
