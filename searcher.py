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

        req = requests.get(url, self.headers)
        req.encoding = "utf-8"
        # try:
        #     req.raise_for_status
        # except requests.HTTPError:
        #     return None
        req.raise_for_status()

        html = req.text
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
            "LOT SIZE",
            "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)",
            "LATITUDE",
            "LONGITUDE",
        )

    def load_house_attributes_from_metro(
        self, metro_name: str, filters_path: str
    ) -> pl.DataFrame:
        house_attributes_df = pl.DataFrame()
        zip_codes = helper.metro_name_to_zip_list(metro_name)
        for zip_code in zip_codes:
            # 5 is zip code length, and this is if we have some issues reading from the file
            zip_code = f"{zip_code:0{5}}"
            url = f"{self.base_url}{self.generate_area_path(zip_code)}{filters_path}"

            try:
                redfin_csv_df = self.df_from_search_page_csv(url)
            except requests.HTTPError as e:
                print(f"Invalid zip: {e}")
                continue

            for listing in redfin_csv_df.rows(named=True):
                pl.concat(
                    [
                        house_attributes_df,
                        pl.DataFrame(
                            {
                                "LATITUDE": listing["LATITUDE"],
                                "LONGITUDE": listing["LONGITUDE"],
                                "ADDRESS": listing["ADDRESS"],
                                "STATE OR PROVINCE": listing["STATE OR PROVINCE"],
                                "ZIP OR POSTAL CODE": listing["ZIP OR POSTAL CODE"],
                                "PRICE": listing["PRICE"],
                                "YEAR BUILT": listing["YEAR BUILT"],
                                "SQUARE FEET": listing["SQUARE FEET"],
                                "LOT SIZE": listing["LOT SIZE"],
                                "HEATING AMENITIES": listing_scraper.heating_amenities_scraper(
                                    listing[
                                        "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
                                    ]
                                ),
                            }
                        ),
                    ]
                )
        return house_attributes_df

    def load_house_attributes_from_zip(
        self, zip_code: int, filters_path: str
    ) -> pl.DataFrame:
        # schema = {
        #     "LATITUDE": pl.Float64,
        #     "LONGITUDE": pl.Float64,
        #     "ADDRESS": str,
        #     "STATE OR PROVINCE": str,
        #     "ZIP OR POSTAL CODE": pl.Int64,
        #     "PRICE": pl.UInt32,
        #     "YEAR BUILT": pl.Int64,
        #     "SQUARE FEET": pl.Int64,
        #     "LOT SIZE": pl.Int64,
        #     "HEATING AMENITIES": pl.Struct,
        # }
        # house_attributes_df = pl.DataFrame(schema=schema)
        listing_dfs_to_append = []
        zip_code = f"{zip_code:0{5}}"
        url = f"{self.base_url}{self.generate_area_path(zip_code)}{filters_path}"

        try:
            # this is the only place where this error should pop up. if a zip is invalid, it is simply ignored
            redfin_csv_df = self.df_from_search_page_csv(url)
        except requests.HTTPError:
            print("Invalid zip")

        # all houses that meet criteria are in this df
        for listing in redfin_csv_df.rows(named=True):
            listing_info_dict = {
                "LATITUDE": listing["LATITUDE"],
                "LONGITUDE": listing["LONGITUDE"],
                "ADDRESS": listing["ADDRESS"],
                "STATE OR PROVINCE": listing["STATE OR PROVINCE"],
                "ZIP OR POSTAL CODE": listing["ZIP OR POSTAL CODE"],
                "PRICE": listing["PRICE"],
                "YEAR BUILT": listing["YEAR BUILT"],
                "SQUARE FEET": listing["SQUARE FEET"],
                "LOT SIZE": listing["LOT SIZE"],
                "HEATING AMENITIES": listing_scraper.heating_amenities_scraper(
                    listing[
                        "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)"
                    ]
                ),
            }
            listing_dfs_to_append.append(pl.DataFrame(listing_info_dict))
            # print("Adding listing to data frame to dataframe")
            # house_attributes_df = pl.concat(
            #     [house_attributes_df, listing_info_df], how="vertical_relaxed"
            # )
            # print(f"Add listings added so far: {house_attributes_df.head()}")
        return pl.concat(listing_dfs_to_append)


# if __name__ == "__main__":
#     # d = RedfinSearcher()
#     # #! handle this case. probably just print something, then exit
#     # f = requests.get("https://www.redfin.com/zipcode/56998")
#     # print(f.status_code)
#     helper.req_get_to_file(
#         requests.get(
#             "https://www.redfin.com/zipcode/55424/filter/sort=hi-sale-date,property-type=house,min-year-built=2022,max-year-built=2022,include=sold-5yr"
#         )
#     )
