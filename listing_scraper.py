from bs4 import BeautifulSoup as btfs
from bs4 import element
import requests
import re
import helper


def amenity_item_to_dict(tag: element.Tag) -> dict | str:
    """Amenity groups have amenities listed in them with <li> tags. Furthermore,
    amenities come in two types, key: value, and value. This function returns the
    string, or a dict of the key: value pair.

    Args:
        tag (element.Tag): The <li> tag

    Returns:
        amenity: dictionary or string representation of amenity
    """
    #! for our regex parse thing that will categorize , it will be after this. what should be returned from "get housing amenities" is a list
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


def clean_heating_info_dictionary(raw_heating_info_dict: dict) -> dict:
    """Takes in a raw amenity heating info dictionary and only returns relevant heating information.

    Args:
        raw_heating_info_dict (dict): heating info dictionary from web scraping result

    Returns:
        dict: cleaned heating info dictionary
    """
    heating_info_dict = {}
    #! this is what i was talking about
    heating_string = re.compile(r"heat", re.I)
    fuel_string = re.compile(r"fuel", re.I)

    for key, value in raw_heating_info_dict.items():
        if re.search(heating_string, key) or re.search(fuel_string, key):
            heating_info_dict[key] = value

    return heating_info_dict


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
    #! refactor all this junk
    #! https://www.redfin.com/VA/Great-Falls/952-Walker-Rd-22066/home/174503330 has heat pump in utilities info
    # "Forced Air, Heat Pump(s)
    # Heating Fuel: Propane - Leased, Electric"
    req = helper.req_get_wrapper(url)
    req.raise_for_status()
    html = req.text
    soup = btfs(html, "html.parser")
    #! make more robust? i did it somewhere. it doesnt have the boundary token
    cur_elem = soup.find("div", string=re.compile(r"heating\b", re.I))

    if cur_elem is None:
        # in production this should alert something to investigate. the local mls may have another format.
        # the other option is there is no heating info.
        return {}
        # raise ValueError("No heating information")

    heating_dict = {}
    # finding the heating amenity group.
    for sibling in cur_elem.next_siblings:
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

    # we are now in the <ul>
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
    return clean_heating_info_dictionary(heating_dict)
