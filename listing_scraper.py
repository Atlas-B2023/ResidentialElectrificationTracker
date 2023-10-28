from bs4 import BeautifulSoup as btfs
from bs4 import element
import re
import helper

logger = helper.logger

# re.compile(r"heat", re.I), is not included as we dont care if it has heating, we care the type. "has heating" isnt really useful
heating_related_patterns = [
    re.compile(r"fuel", re.I),
    re.compile(r"forced", re.I),
    re.compile(r"(natural)\s(gas)", re.I),
    re.compile(r"gas", re.I),
    re.compile(r"oil", re.I),
    re.compile(r"electricity", re.I),
    re.compile(r"(heat)\s(pump)", re.I),
    re.compile(r"propane", re.I),
    re.compile(r"base", re.I),
    re.compile(r"mini[\s-]split", re.I),
    re.compile(r"pellet", re.I),
    re.compile(r"wood", re.I),
    re.compile(r"radiant", re.I),
]


def _amenity_item_to_str(tag: element.Tag) -> str:
    """Amenity groups have amenities listed in them with <li> tags. These
    amenities come in two types, key: value, and value. To get all items in a list, call this function in a loop

    Args:
        tag (element.Tag): The <li> tag

    Returns:
        amenity: dictionary or string representation of amenity
    """
    #! for our regex parse thing that will categorize , it will be after this. what should be returned from "get housing amenities" is a list
    spans = tag.find("span")
    if spans is None:
        #! should probably error here
        logger.critical("Blank <li> tag on listing page. investigate further")
        return ""

    # sometimes they have weird spacing, just normalizing
    span_split_text = re.sub(r"\s+", " ", spans.text)

    return span_split_text
    #! do we even need all this? all were going to be looking for in the end is fuel type/ burner/heat maker type...


def _clean_heating_info_list(raw_heating_info_list: list[str]) -> list[str]:
    """Takes in a raw amenity heating info dictionary and only returns relevant heating information.

    Args:
        raw_heating_info_dict (dict): heating info dictionary from web scraping result

    Returns:
        dict: cleaned heating info dictionary
    """

    # for elem in list:
    # if elem matches pattern, add to list
    # return list
    # here we just care that anything matches, not categorizing yet
    heating_info_list = []

    for string in raw_heating_info_list:
        if any(regex.findall(string) for regex in heating_related_patterns):
            heating_info_list.append(string)

    return heating_info_list


# this will probably be inside of a func called scrape_housing_information
def heating_amenities_scraper(url: str) -> list[str]:
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
    #! make more robust? might have to loop over a select few amenity super groups
    cur_elem = soup.find("div", string=re.compile(r"heating\b", re.I))

    if cur_elem is None:
        # in production this should alert something to investigate. the local mls may have another format.
        # the other option is there is no heating info.
        # make search strings a list, then compile the list. use the string list here
        logger.info("No div matching pattern \"heating\"")
        return []
        # raise ValueError("No heating information")

    heating_list = []
    # finding the heating amenity group.
    for sibling in cur_elem.next_siblings:
        if sibling.name == "li":  # type: ignore
            # heating fuel: x, natural gas; has heating;

            amenity_item = _amenity_item_to_str(sibling)
            if amenity_item != "":
                heating_list.append(amenity_item)

    # handles the <ul>'s dangling <li> tags. Guards for the case when there is no <ul>
    count = 0
    while cur_elem.name != "ul":
        cur_elem = cur_elem.parent
        count += 1
        if count > 3:
            # all of the amenities have been added to the dict. now we're in no man's land
            return heating_list

    # we are now in the <ul>
    for child in cur_elem.children:
        if child.name == "li":
            amenity_item = _amenity_item_to_str(child)
            if amenity_item != "":
                heating_list.append(amenity_item)
    
    cleaned_heating_info_list = _clean_heating_info_list(heating_list)
    if len(cleaned_heating_info_list) == 0:
        logger.info("No heating amenities found") # for {address}
    else:
        logger.info("Heating amenities found")
    return cleaned_heating_info_list
