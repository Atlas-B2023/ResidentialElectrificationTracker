import polars as pl
from redfin import Redfin
from enum import StrEnum
import requests
import time
import random


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


def state_county_to_zip_df(state: str, county: str) -> pl.DataFrame:
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


def state_city_to_zip_df(state: str, city: str) -> pl.DataFrame:
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


def is_valid_zipcode(zip: int) -> bool:
    # going to treat zips as numbers here, reevaluate later
    df = pl.read_csv("./augmenting_data/uszips.csv")

    return zip in df["ZIP"]


# when making class, init the csv and have it open in memory. not too much and saves on making the df every call
def metro_name_to_zip_code_list(name: str) -> list[int]:
    """Returns a list of zip codes in the given Metropolitan. Returns nothing if metropolitan name is invalid.

    Args:
        name (str): Name of the Metropolitan

    Returns:
        list[int]: List of zip codes found
    """
    #! for testing
    if name == "TEST":
        # 22066 has a lot which raises the line 90 listing scraper error
        return [22067, 55424, 33629]
        # return [22067, 55424]

    df = pl.read_csv("./augmenting_data/master.csv")

    # MSAs are what were looking for in this project
    result = df.filter(
        (df["METRO_NAME"] == name) & (df["LSAD"] == "Metropolitan Statistical Area")
    )["ZIP"]

    if len(result) > 0:
        return result.to_list()
    else:
        return []


def zip_to_metro(zip: int) -> str:
    """Finds the Metropolitan area name for the corresponding zipcode, or an empty string if it is not a part of a metropolitan

    Args:
        zip (int): Zip code to look up

    Returns:
        str: the Metropolitan name
    """
    df = pl.read_csv("./augmenting_data/master.csv")

    result = df.filter(df["ZIP"] == zip)["METRO_NAME"]

    if len(result) > 0:
        return result[0]
    else:
        return "    "


def get_random_user_agent() -> str:
    list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
        "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
        "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Mozilla/5.0 (Android 12; Mobile; rv:109.0) Gecko/113.0 Firefox/113.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    ]
    return random.choice(list)


def req_get_wrapper(url: str) -> requests.Response:
    """wrapper for requests. has a sleep and headers

    Args:
        url (str): url

    Returns:
        requests.Response: the response object
    """
    time.sleep(random.uniform(0.6, 1.1))
    req = requests.get(
        url,
        headers={"User-Agent": get_random_user_agent()},
        timeout=17,
    )

    return req


def req_get_to_file(get_request: requests.Response) -> int:
    with open(f"{time.time()}_request.html", "w+", encoding="utf-8") as f:
        f.write(get_request.text)
    return get_request.status_code


def df_to_file(df: pl.DataFrame):
    df.write_csv(f"{time.time()}_data_frame.csv", has_header=True)


if __name__ == "__main__":
    print(
        len(metro_name_to_zip_code_list("Washington-Arlington-Alexandria, DC-VA-MD-WV"))
    )
