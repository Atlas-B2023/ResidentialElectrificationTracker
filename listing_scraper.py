import helper
from bs4 import BeautifulSoup as btfs
from bs4 import element
import requests
import re


def amenity_item_to_dict(tag: element.Tag) -> dict | str:
    """The two cases are a line with a colon and a line without a colon. The line
    is a list element (<li>) with a marker pseudo element, a span for the content
    before the colon, and a span for the content after the element

    Args:
        tag (btfs.PageElement): the li tag

    Returns:
        dict: the content to the left of the colon as the key, and to the right of
        the colon as the value. If there is no colon, the key will be an empty string
    """

    span_split_text = re.sub(r"\s+", " ", tag.find("span").text)
    if ":" in span_split_text:
        span_split_text = span_split_text.split(": ")
    else:
        #if its not like "heating: central", then do this
        return span_split_text
    
    if len(span_split_text) == 2:
        return {span_split_text[0]: span_split_text[1]}
    else:
        return {"amenity_item_to_dict_N/a", "N/a"}


# this will probably be inside of a func called scrape_housing_information


def heating_amenities_scraper(url: str) -> dict:
    """Scrapes when given HTML in the form:
    <div class="amenity-group>
        <ul>
            <div class="no-break-inside">
                <div>Heating...</div>
                <li>
                    <span> *optional*<span> </span></span>
                </li>
                ...
            </div>
                <li class="entryItem">
                    <span> *optional*<span> </span></span>
                </li>
        </ul>
    </div>

    Args:
        url (str): _description_

    Returns:
        dict: _description_
    """
    heating_dict = {}
    html = requests.get(url).text

    soup = btfs(html, "html.parser")

    cur_elem = soup.find("div", string=re.compile(r"heating\b", re.I))
    if cur_elem is None:
        # in production this should alert something to investigate. the local mls may have another format.
        # the other option is there is no heating info.
        raise ValueError("No heating information")

    # handles the insertion point of finding the amenity group.
    for sibling in cur_elem.next_siblings:
        # only want tags
        if sibling.name == "li":
            item = amenity_item_to_dict(sibling)
            if isinstance(item, str):
                if "misc_heating_info" in heating_dict:
                        list = heating_dict.get("misc_heating_info")
                        list.append(item)
                        heating_dict.update({"misc_heating_info": list})
                else:
                    heating_dict.update({"misc_heating_info": [item]})
            else:
                heating_dict.update(item)

    # handles the dangling list items under the ul tag
    while cur_elem.name != "ul":
        cur_elem = cur_elem.parent
        if cur_elem.name == "html":
            raise ValueError("heating_amenities_scraper_uhhh were at html now ")

    # we are now in the ul
    for child in cur_elem.children:
        if child.name == "li":
            item = amenity_item_to_dict(child)
            if isinstance(item, str):
                if "misc_heating_info" in heating_dict:
                        list = heating_dict.get("misc_heating_info")
                        list.append(item)
                        heating_dict.update({"misc_heating_info": list})
                else:
                    heating_dict.update({"misc_heating_info": [item]})
            else:
                heating_dict.update(item)
    return heating_dict


# def get_redfin_listing_from_url(url: str) -> str:
#     """Returns the HTML from a house listing based on the URL

#     Args:
#         url (str): the url of a listing

#     Returns:
#         str: HTML of the house's listing
#     """

# def extract_housing_data(html: str, soup: btfs) -> str:
#     """_summary_

#     Args:
#         html (str): html of the page listing
#         soup (btfs): btfs parser

#     Returns:
#         str: returns the housing data in a schema
#     """

if __name__ == "__main__":
    url = "https://www.redfin.com/NH/Wilton/33-Maple-St-03086/home/88228419"
    print(
        scrape_heating_information(url)
        == {"Cooling": "Mini Split", "Heat": "Radiator, Steam, Mini Split"}
    )
