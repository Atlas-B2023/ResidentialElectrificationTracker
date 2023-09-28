import helper
from bs4 import BeautifulSoup as btfs
from bs4 import element
import requests
import re


def amenity_item_to_dict(tag: element.Tag) -> dict | str:
    """Amenity groups have amenities listed in them with <li> tags. Furthermore, 
    amenities come in two types, key: value, and value. This function returns the 
    string, or a dict of the key: value pair. 

    Args:
        tag (element.Tag): The <li> tag

    Returns:
        amenity: dictionary or string representation of amenity 
    """

    span_split_text = re.sub(r"\s+", " ", tag.find("span").text)
    if ":" in span_split_text:
        span_split_text = span_split_text.split(": ")
    else:
        # if its not like "heating: central", then do this
        return span_split_text

    if len(span_split_text) == 2:
        return {span_split_text[0]: span_split_text[1]}
    else:
        return {"amenity_item_to_dict_N/a", "N/a"}


# this will probably be inside of a func called scrape_housing_information
def heating_amenities_scraper(url: str) -> dict:
    """Scrapes amenity info when the given HTML is in the form:
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
        url (str): The listing page

    Returns:
        amenities: dict representation of all amenities
    """
    html = requests.get(url).text
    soup = btfs(html, "html.parser")
    cur_elem = soup.find("div", string=re.compile(r"heating\b", re.I))
    heating_dict = {}

    if cur_elem is None:
        # in production this should alert something to investigate. the local mls may have another format.
        # the other option is there is no heating info.
        raise ValueError("No heating information")

    # finding the heating amenity group.
    for sibling in cur_elem.next_siblings:
        # only want li tags
        if sibling.name == "li":
            # if we have a string, the amenity stands alone in the html. we typically dont care about these, so they're
            # all grouped under a misc info list
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

    # handles the <ul>'s dangling <li> tags. Guards for the case when there is no <ul>
    count = 0
    while cur_elem.name != "ul":
        cur_elem = cur_elem.parent
        count += 1
        if count > 3:
            # all of the amenities have been added to the dict. now we're in no man's land
            return heating_dict

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
