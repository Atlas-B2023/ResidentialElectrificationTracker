import logging
import os
import time
from enum import StrEnum
from pathlib import Path

import polars as pl
import requests
import sys
from .us import states as sts

LOGGING_DIR = Path(__file__).parent.parent.parent / "output" / "logging"
LOGGING_FILE_PATH = LOGGING_DIR / "logging.log"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"

MASTER_DF = pl.read_csv(
    Path(__file__).parent.parent.parent / "augmenting_data" / "master.csv"
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


def is_valid_zipcode(zip: int) -> bool:
    """Check if the given ZIP code is valid based on a local file.

    Args:
        zip (int): the ZIP code to check

    Returns:
        bool: if ZIP code is valid
    """
    if isinstance(zip, str):
        zip = int(zip)
    return zip in MASTER_DF["ZIP"]


def req_get_wrapper(url: str) -> requests.Response:
    time.sleep(0.3)
    req = requests.get(url=url)
    req.raise_for_status()
    req.encoding = "utf-8"
    return req


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
        return [20015, 20018, 20017]  # nulls in sqft and large

    df = MASTER_DF.select("ZIP", "METRO_NAME", "LSAD")

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
    result = MASTER_DF.filter(MASTER_DF["ZIP"] == zip)["METRO_NAME"]

    if len(result) > 0:
        log("Zip has multiple codes. Only giving first one", "debug")
        return result[0]
    else:
        return ""  # should this be none?


def req_get_to_file(request: requests.Response) -> int:
    """Write the contents of a request response to a unique file.

    Args:
        request (requests.Response): the request

    Returns:
        int: the status code of the request
    """
    with open(OUTPUT_DIR / f"{time.time()}_request.html", "w+", encoding="utf-8") as f:
        f.write(request.text)
    return request.status_code


def df_to_file(df: pl.DataFrame):
    """Write a DataFrame to a unique file.

    Args:
        df (pl.DataFrame): the DataFrame to write
    """
    file_path = OUTPUT_DIR / f"{time.time()}_data_frame.csv"
    print(f"Dataframe saved to {file_path.resolve()}")
    df.write_csv(file_path, include_header=True)


def get_unique_msa_from_master() -> pl.Series:
    return (
        MASTER_DF.filter(pl.col("LSAD").eq("Metropolitan Statistical Area"))
        .select("METRO_NAME")
        .unique()
        .to_series()
    )


def get_states_in_msa(msa_name: str) -> list[str]:
    return (
        MASTER_DF.select("STATE_ID", "METRO_NAME", "LSAD")
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
        MASTER_DF.select("STATE_ID", "ZIP")
        .filter(pl.col("STATE_ID").eq(state_code))
        .get_column("ZIP")
        .unique()
        .to_list()
    )

def get_census_report_url_page(search_term: str):
    census_reporter_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
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

def _set_up_logger(level: int) -> logging.Logger:
    """Setup a logger that prints to a file.

    Args:
        level (int): Severity level

    Returns:
        logging.Logger: logger object
    """
    LOGGING_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s: %(message)s", datefmt=date_format
    )
    handler = logging.FileHandler(LOGGING_FILE_PATH, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    logger.info("===============================")
    logger.info("Starting logger.")
    logger.info("===============================")

    return logger

class LoggerWriter:
    def __init__(self, logfct):
        self.logfct = logfct
        self.buf = []

    def write(self, msg):
        if msg.endswith('\n'):
            self.buf.append(msg.removesuffix('\n'))
            self.logfct(''.join(self.buf))
            self.buf = []
        else:
            self.buf.append(msg)

    def flush(self):
        pass


def log(msg, level):
    file_handler = None
    for handler in _logger.handlers:
        if isinstance(handler, logging.FileHandler):
            file_handler = handler
            break

    if file_handler is None:
        print("Logging file handler could not be established")
        exit()

    match level:
        case "debug":
            _logger.debug(msg)
            file_handler.flush()
            os.fsync(file_handler.stream.fileno())
        case "warn", "warning":
            _logger.warning(msg)
            file_handler.flush()
            os.fsync(file_handler.stream.fileno())
        case "error":
            _logger.warning(msg)
            file_handler.flush()
            os.fsync(file_handler.stream.fileno())
        case "critical":
            _logger.warning(msg)
            file_handler.flush()
            os.fsync(file_handler.stream.fileno())
        case _:
            _logger.info(msg)
            file_handler.flush()
            os.fsync(file_handler.stream.fileno())


_logger = _set_up_logger(logging.INFO)

sys.stdout = LoggerWriter(_logger.info)
sys.stderr = LoggerWriter(_logger.error)