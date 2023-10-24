from dotenv import load_dotenv
import os
import requests
import datetime

load_dotenv()

class EIADataRetriever:
    def __init__(self):
        self.eia_base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")

    def energy_price_json_to_dict(self, eia_json) -> dict:
        if (
            eia_json is None
            or "response" not in eia_json
            or "data" not in eia_json["response"]
        ):
            return {}
        return {entry["period"]: entry["price"] for entry in eia_json["response"]["data"]}

    def eia_monthly_energy_price_per_kwh(
        self, state: str, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        url = (
            f'{self.eia_base_url}/electricity/retail-sales/data?data[]=price'
            f'&facets[sectorid][]=RES&facets[stateid][]={state}&frequency=monthly'
            f'&start={start_date}&end={end_date}&sort[0][column]=period'
            f'&sort[0][direction]=asc&api_key={self.api_key}'
        )
        eia_request = requests.get(url)
        if eia_request.status_code == 200:
            return self.energy_price_json_to_dict(eia_request.json())
        else:
            return {}

if __name__ == "__main__":
    data_retriever = EIADataRetriever()
    result = data_retriever.eia_monthly_energy_price_per_kwh(
        "CO", datetime.date(2022, 1, 1), datetime.date(2022, 12, 1)
    )
    print(result)
