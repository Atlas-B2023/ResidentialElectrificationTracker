import re

import Helper as Helper
from bs4 import BeautifulSoup as btfs
from bs4 import element

logger = Helper.logger


heating_related_patterns = [
    re.compile(r"fuel", re.I),
    re.compile(r"furnace", re.I),
    re.compile(r"diesel", re.I),
    re.compile(r"hot\swater", re.I),
    re.compile(r"solar\sheat", re.I),  # Active Solar Heating
    re.compile(r"resist(?:ive|ance)", re.I),
    re.compile(r"space\sheater", re.I),
    re.compile(r"burn", re.I),
    re.compile(r"hybrid\sheat", re.I),
    re.compile(r"(natural)\s(gas)", re.I),
    re.compile(r"gas", re.I),
    re.compile(r"oil", re.I),
    re.compile(r"electric", re.I),
    re.compile(r"(heat)\s(pump)", re.I),
    re.compile(r"propane", re.I),
    re.compile(r"base", re.I),
    re.compile(r"mini[\s-]split", re.I),
    re.compile(r"pellet", re.I),
    re.compile(r"wood", re.I),
    re.compile(r"radiant", re.I),
]


def amenity_item_to_str(tag: element.Tag) -> str:
    """Extract amenity items from their <li> tag. Should be called when dealing with amenity groups.

    Args:
        tag (element.Tag): <li> tag

    Returns:
        str: string representation of amenity item
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


def extract_heating_terms_to_list(terms_list: list[str]) -> list[str]:
    """Extract a list of terms related to heating from a list.

    Note:
        TODO link to this
        Strings are matched based on `heating_related_patterns`.

    Args:
        raw_heating_info_dict (list[str]): list of terms to search through

    Returns:
        list[str]: list of strings dealing with heating
    """

    # here we just care that anything matches, not categorizing yet
    heating_terms_list = []

    for string in terms_list:
        if any(regex.findall(string) for regex in heating_related_patterns):
            heating_terms_list.append(string)

    return heating_terms_list


# TODO this only deals with a div that matches "Heating", but heating information can be in things like "utilities" or "interior"
# Make this a tuple?
def heating_amenities_scraper(address_and_listing_url_list: list[str]) -> list[str]:
    """Scrape amenity info when given HTML of the form:

    ```html
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
    ```

    Args:
        add_url_list (list[str]): The first element is an address, and the second element is the listing page for said address

    Returns:
        list[str]: list of heating amenities found
    """
    address, url = address_and_listing_url_list
    req = Helper.req_get_wrapper(url)
    req.raise_for_status()
    html = req.text
    soup = btfs(html, "html.parser")
    #! make more robust? might have to loop over a select few amenity super groups
    cur_elem = soup.find("div", string=re.compile(r"heating\b", re.I))

    if cur_elem is None:
        # in production this should alert something to investigate. the local mls may have another format.
        # the other option is there is no heating info.
        # make search strings a list, then compile the list. use the string list here
        logger.info('No div matching pattern "heating"')
        return []
        # raise ValueError("No heating information")

    heating_list = []
    # finding the heating amenity group.
    for sibling in cur_elem.next_siblings:
        if sibling.name == "li":  # type: ignore
            # heating fuel: x, natural gas; has heating;

            amenity_item = amenity_item_to_str(sibling)
            if amenity_item != "":
                heating_list.append(amenity_item)

    # handles the <ul>'s dangling <li> tags. Guards for the case when there is no <ul>
    count = 0
    while cur_elem.name != "ul":
        cur_elem = cur_elem.parent
        if cur_elem is None:
            # not really sure what this is
            logger.debug(f"How did we end up here? {cur_elem = }")
            return heating_list

        count += 1
        if count > 3:
            # all of the amenities have been added to the dict. now we're in no man's land
            return heating_list

    # we are now in the <ul>
    for child in cur_elem.children:
        if child.name == "li":
            amenity_item = amenity_item_to_str(child)
            if amenity_item != "":
                heating_list.append(amenity_item)

    cleaned_heating_info_list = extract_heating_terms_to_list(heating_list)
    if len(cleaned_heating_info_list) == 0:
        logger.info(f"{address} does not have heating information.")
    else:
        logger.info(f"{address} has heating information.")
    return cleaned_heating_info_list
