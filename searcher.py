import requests
from bs4 import BeautifulSoup as btfs
import polars as pl
import helper
import listing_scraper


# PURPOSE: this file

# this will probably be called by main. will need a dataframe parameter?
# all urls in code will not have a trailing forward slash in urls
# can either preform url checks before, or wait until everything is formed and do lots of path tracing when we bounce from the endpoint


# look at ways to decuple this class from redfin?
class RedfinSearcher:
    def __init__(self) -> None:
        self.base_url = "https://www.redfin.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        }

    def generate_area_path(self, zip_code_or_city_and_state_or_address: str) -> str:
        # save on a request. have to really check where zips are being treated as strings and ints
        if (
            len(zip_code_or_city_and_state_or_address) == 5
            and zip_code_or_city_and_state_or_address.isdigit()
        ):
            return f"/zipcode/{zip_code_or_city_and_state_or_address}"
        return f"{helper.get_redfin_url_path(zip_code_or_city_and_state_or_address)}"

    def generate_filter_path(self, **kwargs) -> str:
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

        # can do additional checks if wanted, treat param names as filter words
        for key, value in kwargs.items():
            if isinstance(value, list):
                selected_filters.append(f'{key.replace("_","-")}={"+".join(value)}')
            else:
                selected_filters.append(f'{key.replace("_","-")}={value}')

        return f'/filter/{",".join(selected_filters)}'

    def df_from_search_page_csv(self, url: str) -> pl.DataFrame | None:
        """Returns a dataframe schema data from the search results page.

        Args:
            url (str): url of search listings page

        Returns:
            pl.dataframe.frame.DataFrame: dataframe in schema
        """

        req = helper.req_get_wrapper(url)
        req.raise_for_status()

        html = req.content
        soup = btfs(html, "html.parser")
        download_button_id = "download-and-save"
        download_link_tag = soup.find("a", id=download_button_id)
        if download_link_tag is None:
            # should be handled in caller
            raise TypeError(
                "Could not find csv download. Check if the html downloaded is correct, or if the download button id has changed"
            )

        download_link = download_link_tag.get("href")
        if download_link is None:
            raise KeyError(
                f"<a> tag with id {download_button_id} does not exist. Has the HTML id changed?"
            )

        df = pl.read_csv(self.base_url + download_link)
        return df.select(
            "ADDRESS",
            "CITY",
            "STATE OR PROVINCE",
            "YEAR BUILT",
            "ZIP OR POSTAL CODE",
            "PRICE",
            "SQUARE FEET",
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
            "LATITUDE",
            "LONGITUDE",
        )

    def load_house_attributes_from_metro(
        self, metro_name: str, filters_path: str
    ) -> pl.DataFrame:
        zip_codes = helper.metro_name_to_zip_list(metro_name)

        if len(zip_codes) == 0:
            return pl.DataFrame()

        dfs_to_concat = []
        for zip in zip_codes:
            zip_df = self.load_house_attributes_from_zip_code(zip, filters_path)
            if zip_df is not None:
                dfs_to_concat.append(zip_df)

        # if for some reason all attribs are none (probably a bigger issue in creating the master.csv),
        # just give an empty dataframe

        print(f"Dataframes in list: {dfs_to_concat}")
        if len(dfs_to_concat) == 0:
            # untested
            return pl.DataFrame()
        else:
            concat_dfs = pl.concat(dfs_to_concat, how="vertical_relaxed")
            concat_dfs = concat_dfs.with_columns(
                pl.col("SQUARE FEET").cast(pl.Int64)
            )
            return concat_dfs

    def load_house_attributes_from_zip_code(
        self, zip_code: int, filters_path: str
    ) -> pl.DataFrame | None:
        listing_dfs_to_concat = []
        zip_code = f"{zip_code:0{5}}"
        url = f"{self.base_url}{self.generate_area_path(zip_code)}{filters_path}"

        try:
            # this is the only place where this error should pop up. if a zip is invalid,
            # return none and handle in caller. an example is the zip 56998, which is just a
            # USPS distribution center in D.C
            redfin_csv_df = self.df_from_search_page_csv(url)
        except requests.HTTPError:
            print("Invalid zip")
            return None

        # all houses that meet criteria are in this df
        for listing in redfin_csv_df.rows(named=True):
            listing_heating_amenities_dict = listing_scraper.heating_amenities_scraper(
                listing[
                    "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
                ]
            )
            listing_heating_amenities_list = []
            for key in listing_heating_amenities_dict.keys():
                listing_heating_amenities_list.append(key)
                listing_heating_amenities_list.append(listing_heating_amenities_dict.get(key))
            #! this list conversion should be done in the helper method. really hacky
            if len(listing_heating_amenities_list) == 0:
                print(f"House {listing['ADDRESS']} does not have heating information available. Skipping...")
                continue
            
            # look into making heating amenities a list of strings, better for dataframe
            listing_info_dict = {
                "LATITUDE": listing["LATITUDE"],
                "LONGITUDE": listing["LONGITUDE"],
                "ADDRESS": listing["ADDRESS"],
                "STATE OR PROVINCE": listing["STATE OR PROVINCE"],
                "ZIP OR POSTAL CODE": listing["ZIP OR POSTAL CODE"],
                "PRICE": listing["PRICE"],
                "YEAR BUILT": listing["YEAR BUILT"],
                "SQUARE FEET": listing["SQUARE FEET"],
                "HEATING AMENITIES": listing_heating_amenities_list
            }
            listing_dfs_to_concat.append(pl.DataFrame(listing_info_dict))
            print(f"Adding {listing_info_dict['ADDRESS']} to list.")

        return pl.concat(listing_dfs_to_concat, how="vertical_relaxed")

