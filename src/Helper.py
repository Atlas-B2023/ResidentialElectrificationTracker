import logging
import random
import time
from enum import StrEnum
from pathlib import Path

import polars as pl
import requests
from redfin import Redfin

session = requests.Session()
class ASCIIColors(StrEnum):
    """ASCII colors for use in printing colored text to the terminal."""

    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"


def state_county_to_zip_df(state: str, county: str) -> pl.DataFrame:
    """Take in a state and county and return the ZIP code constituents of that county.

    Args:
        state (str): the state
        county (str): the county

    Returns:
        pl.DataFrame: DataFrame of ZIP codes
    """
    return (
        pl.read_csv("zip_registry.csv")
        .filter((pl.col("state") == state) & (pl.col("county") == county))
        .select("zipcode")
    )


def state_city_to_zip_df(state: str, city: str) -> pl.DataFrame:
    """Take in a state and city and return the ZIP code constituents of that city.

    Args:
        state (str): the state
        city (str): the city

    Returns:
        pl.DataFrame: DataFrame of ZIP codes
    """
    return (
        pl.read_csv("zip_registry.csv")
        .filter((pl.col("state") == state) & (pl.col("city") == city))
        .select("zipcode")
    )


def get_redfin_url_path(location: str) -> str:
    """Generate the URL path with the proprietary Redfin number for the given city, ZIP code, or address.

    Examples:
        >>> get_redfin_url_path("Washington D.C")
        "/city/12839/DC/Washington-DC"

    Args:
        location (str): the location

    Returns:
        str: the path to the location
    """
    client = Redfin()
    response = client.search(location)
    return response["payload"]["sections"][0]["rows"][0]["url"]


def is_valid_zipcode(zip: int) -> bool:
    """Check if the given ZIP code is valid based on a local file.

    Args:
        zip (int): the ZIP code to check

    Returns:
        bool: if ZIP code is valid
    """
    # zip codes are stored as numbers in the csv as of 10/28/23
    df = pl.read_csv("./augmenting_data/uszips.csv")

    return zip in df["ZIP"]


# when making class, init the csv and have it open in memory. not too much and saves on making the df every call
def metro_name_to_zip_code_list(msa_name: str) -> list[int]:
    """Return the constituent ZIP codes for the given Metropolitan Statistical Area.

    Args:
        msa_name (str): name of the Metropolitan Statistical Area

    Returns:
        list[int]: list of ZIP codes found. Is empty if MSA name is invalid
    """
    if msa_name == "TEST":
        # return [55424]  # good and small
        # return [22067, 55424]  # nulls in sqft
        return [10101, 90037, 55424, 33617]  # nulls in sqft and large

    df = pl.read_csv("./augmenting_data/master.csv")

    # MSAs are what were looking for in this project. Some MSA are repeated. can use unique(), but using a select is faster and better
    return df.filter(
        (df["METRO_NAME"] == msa_name) & (df["LSAD"] == "Metropolitan Statistical Area")
    )["ZIP"].to_list()


def zip_to_metro(zip: int) -> str:
    """Find the Metropolitan Statistical Area name for the specified ZIP code.

    Args:
        zip (int): the ZIP code to look up

    Returns:
        str: the Metropolitan name. Is empty if the ZIP code is not a part of a Metropolitan Statistical Area
    """
    df = pl.read_csv("./augmenting_data/master.csv")

    result = df.filter(df["ZIP"] == zip)["METRO_NAME"]

    if len(result) > 0:
        return result[0]
    else:
        return "    "


def get_random_user_agent() -> str:
    """Pick a random user agent string from a list of popular user agents.

    Returns:
        str: user agent string
    """
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
    """Wrapper for requests. Uses a random short sleep and random user agent string.

    Args:
        url (str): url to pass to `requests.get()`

    Returns:
        requests.Response: the response object
    """
    time.sleep(random.uniform(0.6, 1.1))
    req = session.get(
        url,
        headers={"User-Agent": get_random_user_agent()},
        timeout=17,
    )

    return req


def req_get_to_file(request: requests.Response) -> int:
    """Write the contents of a request response to a unique file.

    Args:
        request (requests.Response): the request

    Returns:
        int: the status code of the request
    """
    with open(f"{time.time()}_request.html", "w+", encoding="utf-8") as f:
        f.write(request.text)
    return request.status_code


def df_to_file(df: pl.DataFrame):
    """Write a DataFrame to a unique file.

    Args:
        df (pl.DataFrame): the DataFrame to write
    """
    file_path = Path("./output") / f"{time.time()}_data_frame.csv"
    print(f"Dataframe saved to {file_path.resolve()}")
    df.write_csv(file_path, has_header=True)


def _set_up_logger(level: int) -> logging.Logger:
    """Setup a logger object with basic config.

    Args:
        level (int): Severity level

    Returns:
        logging.Logger: logger object
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s: %(message)s", datefmt=date_format
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)
    logger.propagate = False

    return logger


logger = _set_up_logger(logging.INFO)
