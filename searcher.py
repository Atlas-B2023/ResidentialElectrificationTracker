import requests
from bs4 import BeautifulSoup as btfs
import polars as pl
from helper import (
    Sort,
    PropertyType,
    Include,
    Status,
    get_redfin_url_path,

)
#PURPOSE: this file 

# this will probably be called by main. will need a dataframe parameter
# all urls in code will not have a trailing forward slash in urls
# can either preform url checks before, or wait until everything is formed and do lots of path tracing when we bounce from the endpoint
base_url = "https://www.redfin.com"

# check zip against file? or just use that file for input validation at the gui level
def generate_area_url(zipcode_or_city_and_state_or_address: str) -> str:
    #save on a request
    if len(zipcode_or_city_and_state_or_address) == 5 and zipcode_or_city_and_state_or_address.isdigit():
        return f"/zipcode/{zipcode_or_city_and_state_or_address}"
    return f"{get_redfin_url_path(zipcode_or_city_and_state_or_address)}"


def generate_filter_url(**kwargs) -> str:
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


def csv_from_search_page_url_polars(url: str) -> pl.dataframe.frame.DataFrame:
    """Returns a dataframe schema data from the search results page.

    Args:
        url (str): url of search listings page

    Returns:
        pl.dataframe.frame.DataFrame: dataframe in schema
    """

    html = requests.get(url).text
    soup = btfs(html, 'html.parser')
    download_button_id = "download-and-save"
    download_link_tag = soup.find("a", id=download_button_id)
    if download_link_tag is None:
        #should be handled in caller
        return pl.DataFrame(columns=[
        "ADDRESS",
        "CITY",
        "STATE OR PROVINCE",
        "YEAR BUILT",
        "PRICE",
        "SQUARE FEET",
        "$/SQUARE FEET",
        "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
    ])
    
    download_link = download_link_tag.get('href')
    if download_link is None:
        raise KeyError(f'"a" tag with id {download_button_id} does not exist. Has the HTML id changed?')

    df = pl.read_csv(base_url + download_link)
    return df.select(
        "ADDRESS",
        "CITY",
        "STATE OR PROVINCE",
        "YEAR BUILT",
        "ZIP OR POSTAL CODE",
        "PRICE",
        "SQUARE FEET",
        "$/SQUARE FEET",
        "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
    )


if __name__ == "__main__":
    print(generate_area_url("33 Maple St, Wilton, NH 03086"))
    # # area_url = generate_area_url(("Portland", "Maine"))
    # area_url = generate_area_url("04103")
    # # print(area_url)
    # filter_url = generate_filter_url(
    #     sort=Sort.MOST_RECENT_SOLD,
    #     property_type=PropertyType.HOUSE,
    #     min_year_built=2022,
    #     include=Include.LAST_3_YEAR,
    # )
    # no_input_filter_url = 0
    # search_page_url = base_url + area_url + filter_url
    # print(search_page_url)
    # # print(req_get_to_file(requests.get(search_page_url)))
    # df = csv_from_search_page_url_polars(search_page_url)
    # print(df.shape)
    # df_to_file(df)
