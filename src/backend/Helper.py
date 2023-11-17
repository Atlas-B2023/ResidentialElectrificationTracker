import logging
import os
import random
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

import polars as pl
import requests
from fake_useragent import UserAgent
from redfin import Redfin

from .us import states as sts

redfin_session = requests.Session()
master_df = pl.read_csv(
    f"{Path(os.path.dirname(__file__)).parent.parent}{os.sep}augmenting_data{os.sep}master.csv"
)
CENSUS_REPORTER_API_BASE_URL = "https://api.censusreporter.org"
CENSUS_REPORTER_BASE_URL = "https://censusreporter.org"


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
    if isinstance(zip, str):
        zip = int(zip)
    return zip in master_df["ZIP"]


# when making class, init the csv and have it open in memory. not too much and saves on making the df every call
def metro_name_to_zip_code_list(msa_name: str) -> list[int]:
    """Return the constituent ZIP codes for the given Metropolitan Statistical Area.

    Args:
        msa_name (str): name of the Metropolitan Statistical Area

    Returns:
        list[int]: list of ZIP codes found. Is empty if MSA name is invalid
    """
    if msa_name == "TEST":
        # return [20814]  # good and small
        # return [22067, 55424]  # nulls in sqft
        return [10101, 90037, 1609, 33617, 80206, 60624]  # nulls in sqft and large
    # path = f"{Path(os.path.dirname(__file__)).parent.parent}{os.sep}augmenting_data{os.sep}uszips.csv"

    df = master_df.select("ZIP", "METRO_NAME", "LSAD")
    # pl.read_csv(
    #     "./augmenting_data/master.csv", columns=["ZIP", "METRO_NAME", "LSAD"]
    # )

    # MSAs are what were looking for in this project.
    return (
        df.filter(
            (pl.col("METRO_NAME").eq(msa_name))
            & (pl.col("LSAD").eq("Metropolitan Statistical Area"))
        )
        .unique()["ZIP"]
        .to_list()
    )


def zip_to_metro(zip: int) -> str:
    """Find the Metropolitan Statistical Area name for the specified ZIP code.

    Args:
        zip (int): the ZIP code to look up

    Returns:
        str: the Metropolitan name. Is empty if the ZIP code is not a part of a Metropolitan Statistical Area
    """
    result = master_df.filter(master_df["ZIP"] == zip)["METRO_NAME"]

    if len(result) > 0:
        logger.debug("Zip has multiple codes. Only giving first one")
        return result[0]
    else:
        return ""  # should this be none?


def req_get_wrapper(url: str) -> requests.Response:
    """Wrapper for requests. Uses a random short sleep and random user agent string. DO NOT USE

    Args:
        url (str): url to pass to `requests.get()`

    Returns:
        requests.Response: the response object
    """
    time.sleep(random.uniform(0.6, 1.1))
    ua = UserAgent(min_percentage=0.1)
    req = redfin_session.get(
        url,
        headers={"User-Agent": ua.random},
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


def get_unique_msa_from_master() -> pl.Series:
    return (
        master_df.filter(pl.col("LSAD").eq("Metropolitan Statistical Area"))
        .select("METRO_NAME")
        .unique()
        .to_series()
    )


def get_states_in_msa(msa_name: str) -> list[str]:
    return (
        master_df.select("STATE_ID", "METRO_NAME", "LSAD")
        .filter(
            (
                pl.col("METRO_NAME").eq(msa_name)
                & pl.col("LSAD").eq("Metropolitan Statistical Area")
            )
        )
        .get_column("STATE_ID")
        .unique()
        .to_list()
    )


def get_zip_codes_in_state(state: str) -> list[str]:
    state_code = sts.lookup(state)
    if state_code is not None:
        state_code = state_code.abbr
    else:
        return []
    return (
        master_df.select("STATE_ID", "ZIP")
        .filter(pl.col("STATE_ID").eq(state_code))
        .get_column("ZIP")
        .unique()
        .to_list()
    )


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
    logger.addHandler(handler)
    logger.propagate = False

    return logger


logger = _set_up_logger(logging.INFO)


def get_census_report_url_page(search_term: str):
    ua = UserAgent(min_percentage=0.1)
    census_reporter_headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Dnt": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
    }
    req = requests.get(
        f"{CENSUS_REPORTER_API_BASE_URL}/2.1/full-text/search?q={search_term}",
        headers=census_reporter_headers,
    )
    req.raise_for_status()
    req_json = req.json()
    profile_url = req_json["results"][0].get("url")

    return f"{profile_url}"
