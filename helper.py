import polars as pl
from redfin import Redfin
from enum import StrEnum
import requests
import time
import random


def state_county_to_zip_df(state: str, county: str) -> pl.dataframe.DataFrame:
    """takes in a state and county and returns the zip code constituents of that county

    Args:
        state (str): the
        county (str): the county

    Returns:
        pl.dataframe.DataFrame: data frame of zip codes
    """
    return (
        pl.read_csv("zip_registry.csv")
        .filter((pl.col("state") == state) & (pl.col("county") == county))
        .select("zipcode")
    )


def state_city_to_zip_df(state: str, city: str) -> pl.dataframe.DataFrame:
    """takes in a state and city and returns the zip code constituents of that city

    Args:
        state (str): the
        city (str): the city

    Returns:
        pl.dataframe.DataFrame: data frame of zip codes
    """
    return (
        pl.read_csv("zip_registry.csv")
        .filter((pl.col("state") == state) & (pl.col("city") == city))
        .select("zipcode")
    )


# get_redfin_city_state_url_path
def get_redfin_url_path(address: str) -> str:
    """Will generate the path for city, zipcode, and addresses
    Args:
        city (str): the city or county to look up
        state (str): the state in which the city resides

    Returns:
        str: returns path to city/county number, state, and city/county, like /city/20420/MA/Worcester
    """
    client = Redfin()
    response = client.search(address)
    return response["payload"]["sections"][0]["rows"][0]["url"]

def rate_limiter():
    #this will freeze the whole thread. make sure GUI is on a different thread, or use something like 
    # import asyncio; async def...; await asyncio.sleep()
    # or singleshot, qWait, et
    time.sleep(random.uniform(1.5,3.5))


# enums


class PropertyType(StrEnum):
    HOUSE = "house"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    OTHER = "other"
    MANUFACTURED = "manufactured"
    COOP = "co-op"
    MULTIFAMILY = "multifamily"


class Status(StrEnum):
    ACTIVE = "active"
    COMINGSOON = "comingsoon"
    CONTINGENT = "contingent"
    PENDING = "pending"


class Include(StrEnum):
    """Sold times are cumulative. When sorting by last sold, the houses that
    show up in the 1 week search will be the first ones to show up in the last 1 year search, for example
    """

    LAST_1_WEEK = "sold-1wk"
    LAST_1_MONTH = "sold-1mo"
    LAST_3_MONTHS = "sold-3mo"
    LAST_6_MONTHS = "sold-6mo"
    LAST_1_YEAR = "sold-1yr"
    LAST_2_YEAR = "sold-2yr"
    LAST_3_YEAR = "sold-3yr"
    LAST_5_YEAR = "sold-5yr"


class Sort(StrEnum):
    # for sale only
    NEWEST = "lo-days"
    # sold only
    MOST_RECENT_SOLD = "hi-sale-date"
    LOW__TO_HIGH_PRICE = "lo-price"
    HIGH_TO_LOW_PRICE = "hi-price"
    SQFT = "hi-sqft"
    LOT_SIZE = "hi-lot-sqf"
    PRICE_PER_SQFT = "lo-dollarsqft"


def is_valid_zipcode(zipcode: int) -> bool:
    return True


def req_get_to_file(get_request: requests.Response) -> int:
    with open(f"{time()}_request.html", "w", encoding="utf-8") as f:
        f.write(get_request.text)
    return get_request.status_code


def df_to_file(df: pl.dataframe.frame.DataFrame):
    df.write_csv(f"{time()}_data_frame.csv", has_header=True)
