import requests
from bs4 import BeautifulSoup as btfs
import polars as pl
from helper import get_redfin_url_path


# PURPOSE: this file

# this will probably be called by main. will need a dataframe parameter?
# all urls in code will not have a trailing forward slash in urls
# can either preform url checks before, or wait until everything is formed and do lots of path tracing when we bounce from the endpoint
base_url = "https://www.redfin.com"


# check zipcode against file? or just use that file for input validation at the gui level
def generate_area_path(zipcode_or_city_and_state_or_address: str) -> str:
    # save on a request
    if (
        len(zipcode_or_city_and_state_or_address) == 5
        and zipcode_or_city_and_state_or_address.isdigit()
    ):
        return f"/zipcode/{zipcode_or_city_and_state_or_address}"
    return f"{get_redfin_url_path(zipcode_or_city_and_state_or_address)}"


def generate_filter_path(**kwargs) -> str:
    # available_filters = [
    #     "include",
    #     "property-type",
    #     "min-beds",
    #     "max-beds",
    #     "min-baths",
    #     "max-baths",
    #     "min-year-built",
    #     "max-year-built",
    #     "status",
    #     "min-price",
    #     "max-price",
    #     "sort",
    #     "exclude-age-restricted",
    #     "is-green",
    #     "fireplace",
    # ]
    selected_filters = []

    # can do additional checks if wanted
    for key, value in kwargs.items():
        if isinstance(value, list):
            selected_filters.append(f'{key.replace("_","-")}={"+".join(value)}')
        else:
            selected_filters.append(f'{key.replace("_","-")}={value}')

    return f'/filter/{",".join(selected_filters)}'


def csv_from_search_page_url(url: str) -> pl.DataFrame | None:
    """Returns a dataframe schema data from the search results page.

    Args:
        url (str): url of search listings page

    Returns:
        pl.dataframe.frame.DataFrame: dataframe in schema
    """

    html = requests.get(url).text
    soup = btfs(html, "html.parser")
    download_button_id = "download-and-save"
    download_link_tag = soup.find("a", id=download_button_id)
    if download_link_tag is None:
        # should be handled in caller
        return None
        # pl.DataFrame(
        #     columns=[
        #         "ADDRESS",
        #         "CITY",
        #         "STATE OR PROVINCE",
        #         "YEAR BUILT",
        #         "ZIP OR POSTAL CODE",
        #         "PRICE",
        #         "SQUARE FEET",
        #         "$/SQUARE FEET",
        #         "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
        #     ]
        # )

    download_link = download_link_tag.get("href")
    if download_link is None:
        raise KeyError(
            f"<a> tag with id {download_button_id} does not exist. Has the HTML id changed?"
        )

    df = pl.read_csv(base_url + download_link)
    return df.select(
        "ADDRESS",
        "CITY",
        "STATE OR PROVINCE",
        "YEAR BUILT",
        "ZIP OR POSTAL CODE",
        "PRICE",
        "SQUARE FEET",
        "LOT SIZE",
        "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
        "LATITUDE",
        "LONGITUDE",
    )
