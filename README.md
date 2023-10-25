# Redfin

## To search a city, construct a URL like the following

https://www.redfin.com/city/\<CITYNUMBER>/\<2CHARSTATECODE>/\<CITY-NAME>

## To search for county, construct a URL like the following

https://www.redfin.com/county/\<COUNTYNUMBER>\<2CHARSTATECODE>/\<COUNTY-NAME>

## To filter the results, append to following to the base URL

/filter/\<FILTERS>

## Types of filters

Different filters can be combined by use of a comma: ,. Options for the same filter can be appended together by using the plus symbol: +. If all options are desired, do not input a filter.

\<filter-name>=
|-\<filter-option>

property-type=

    |-house
    |-condo
    |-townhouse
    |-land
    |-other
    |-manufactured
    |-co-op
    |-multifamily

min-beds=

    |-\<number>

max-beds=

    |-\<number>

min-baths=

    |-\<decimal>

max-baths=

    |-\<decimal>

min-year-built=

    |-\<number>

max-year-built=

    |-\<number>

status=

    |-active
    |-comingsoon
    |-contingent
    |-pending

min-price=

    |-\<decimal, eg: 300.05k>

max-price=

    |-\<decimal, eg: 6M>

sort=

    |-lo-days
    |-hi-lot-sqf
    |-lo-price
    |-lo-dollarsqft
    |-hi-price
    |-hi-sqft
    |-hi-sale-date

include=

    |-sold-1wk
    |-sold-1mo
    |-sold-3mo
    |-sold-6mo
    |-sold-1yr
    |-sold-2yr
    |-sold-3yr
    |-sold-5yr

exclude-age-restricted

is-green

fireplace

## Words on filters

Some filters only work in combination with certain search modes. These are "For Sale" and "Sold". These will be correctly implemented in code, and will have feature parity with the redfin website.

## Rate Limiting

Since searches can contain a high amount of houses, and therefore potentially requests, there is a rate limit. This can be adjusted if desired. I timed myself looking up and searching for heating information and came up with about 3 seconds per listing.

Currently respects robots.txt. Looking into what /\*/amp? is

avm is automated valuation model

## HAR Files
~~In order to get sold listings, you must zoom in on the map and save a har file of the network.~~

~~The file to analyze is similar to https://www.redfin.com/stingray/api/gis/avm?al=1&poly=-117.69722%2034.09242%2C-117.69516%2034.09242%2C-117.69516%2034.09374%2C-117.69722%2034.09374%2C-117.69722%2034.09242&v=8, and is started by "{}&&{"version":502,"errorMessage":"Success","resultCode":0,"payload":{"homes":[{"mlsId":{"label":"MLS#"" Since panning can create intersecting listings,
the entry and connections should be limited to new listings not seen before~~

Sold listings in the last 5 years, which is within our use case can be accessed without making a HAR parser
# Storage

Storage is handled in a local database. Currently looking at SQLite (sqlite3). It has the following schema:

> {address, zipcode, yearbuilt, price, sqft, heatingtype}

### Considerations of elements of schema

price: This will be the last sold price. If a house has not been sold yet, it will be the list price. Since Redfin's estimate is made through machine learning, we would like to not use it. If need be, the property tax valuation of the home is listed, and can be used.

yearbuilt: since we are only collecting recent data, and since we can filter by year built through Redfin, this will be the value. Last selling year is not a useful metric so it is not included in our schema.

heatingtype: this can take many forms. Some houses are hybrid, some have limited information available. Here is a non exhaustive list of some English found for heating system descriptions

> Baseboard Heat, Hot Water, Multi-Zone Heat; Heat Fuel: Propane; Water Heater Off Heating System, On Demand Water Heater, Tankless Water Heater

_Note: Baseboard heat comes in two styles, electric and heated water. This case seems to be heated water._

> Heating: Central

> Heating: Forced Air

> Heating: Heat pump

> Heating: Electric

> Heating: Natural Gas

> Air Conditioning Type: Central;
> Heating Type: Central

> Cooling: Mini Split; Heat: Radiator, Steam, Mini Split; Heat Fuel: Oil

# Realtor.com

robots.txt forbids using their search page. No unofficial api, so cannot search. No TOS though. Allowed to use listing page.

2.9.4
You will not, directly or indirectly, display, post, disseminate, distribute, publish, broadcast, transfer, sell, or sublicense, any information provided through the Services to another individual or entity. This prohibition expressly includes "scraping" (including screen and database scraping), "data mining", or any other activity intended to collect, store, re-organize, summarize, or manipulate any information provided or any related data.
# Zillow

Zillow Group does not allow scraping nor storage of their listing data. This includes through their api, and only allows dynamic data

Q: Can we store Zillow data through the Bridge API?

A: No. You may use the API only to retrieve and display dynamic content from Zillow. You are not permitted to store information locally.

# Homes.com

Not allowed on /routes/ or /services/

from TOS: 
Copyright in the Services is owned by CoStar Group, Inc, an affiliate of Homes, and the Services may only be used for informational purposes. The content displayed on the Services, including but not limited to the website’s look and feel, layout, text, graphics, images, sound or video materials, designs, the URL and software (collectively “Content”), is either the property of, or used with permission by CoStar Group, Inc. and is protected by United States and international copyright and trademark laws. All rights, including but not limited to, copyright, title and interest in the Content belong to CoStar Group, Inc. and/or its respective owners. The compilation (meaning the collection, arrangement and assembly) of all Content on the Services is also the exclusive property of CoStar and/or its respective owners and protected by U.S. and international copyright laws.

You are strictly prohibited from reproducing, republishing, copying, transmitting, distributing in any form, or by any means, any Content.

Without limiting the generality of the other restrictions set forth herein, you may not access, conduct automated queries, monitor or copy any Content or other information of the Services using any “robot”, “spider”, “deep link”, “scraper”, “crawlers”, or other automated means, methodology, algorithm or device or any manual process for any purpose.

# Movoto.com

This is a wordpress site, not sure if that has any implications...

Allowed to use Allow: /api/dosearch/, may be worth looking into. does not listing housing features...
You agree that you will not copy, reproduce, alter, modify, retransmit, redistribute decompile, disassemble, reverse engineer, or create derivative works from the Service, Site or their underlying software. You also agree not to use any automated or manual process, robot, spider or screen-scraper to copy or monitor any part of the Service. By submitting a query or otherwise reviewing the information on this website concerning real property listings (the “Data”) you agree to the following: (i)you will not access the Data through automated or high-volume means; and (ii) you will not “scrape,” harvest or otherwise copy the Data except pursuant to your personal non-commercial use of the Data solely to identify real property listings that you may be interested in investigating further.

# Estately.com

You will use the Service strictly in accordance with these Terms, all Documentation, the Privacy Policy, and Applicable Law. You will not engage in any of the following activities:
(iv) use, modify, copy, or create derivative works from the Service or Marks without the applicable owner's written permission, including without limitation using automated or manual means to access copy content from the Service;

# Homefinder.com

Among other things, you agree not to:

except with the express written permission of Teacup, modify, copy, distribute, transmit, display, perform, reproduce, publish, license, create derivative works from, frame in another Web page, use on any other Web site or application, transfer or sell any information, software, lists of users, databases or other lists, products or services provided through or obtained from the Network, including without limitation, engaging in the practices of “screen scraping,” “database scraping,” or any other activity with the purpose of obtaining lists of users or other information;

# Paid APIS

there are many paid apis that do what we want. a simple one looks like https://app.rentcast.io/app/api. brdige, corelogics, and others also exist. some lists
https://realtyna.com/mls-router-api/
https://www.realestateapi.com/
https://rapidapi.com/realtymole/api/realty-mole-property-api
# Energy

[WattBuy](https://wattbuy.com/en/) seems to have information on costs. look at [api](https://wattbuy.readme.io/reference/creating-an-account). "You are restricted from caching Licensed Content or any other output of WattB's APIs." Probably should just use [OpenEI](https://apps.openei.org/USURDB/).

# GIS

https://gisgeography.com/python-libraries-gis-mapping/

# Census 

https://www.census.gov/data/developers/data-sets.html

pop api:

https://www.census.gov/data/developers/data-sets/popest-popproj/popest.html

> If specified criteria are met, a metropolitan statistical area containing a single core with a population of 2.5 million or more may be subdivided to form smaller groupings of counties referred to as "metropolitan divisions."

https://www.census.gov/programs-surveys/metro-micro/about/glossary.html

https://www.nber.org/research/data/census-core-based-statistical-area-cbsa-federal-information-processing-series-fips-county-crosswalk

# Redivis

https://redivis.com/datasets/dbhp-0vj8t27f9

# EIA

Using EIA v2 api for electricity prices by month per state. API key is free

https://www.eia.gov/opendata/pdf/EIA-APIv2-HandsOn-Webinar-11-Jan-23.pdf
https://www.eia.gov/opendata/?category=0
https://www.eia.gov/opendata/documentation.php

# Project

Metros chosen:

Minneapolis-St. Paul-Bloomington, MN-WI
Tampa-St. Petersburg-Clearwater, FL
Washington-Arlington-Alexandria, DC-VA-MD-WV
