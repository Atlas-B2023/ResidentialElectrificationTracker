# Redfin

Refer to the RedfinSearcher documentation on how to use the program.

## Rate Limiting

Since searches can contain a high amount of houses, and therefore potentially requests, there is a rate limit. This can be adjusted if desired. I timed myself looking up and searching for heating information and came up with about 3 seconds per listing.

Currently respects robots.txt. Looking into what /\*/amp? is

avm is automated valuation model

# Listing sites to consider

## Realtor.com

robots.txt forbids using their search page. No unofficial api, so cannot search. No TOS though. Allowed to use listing page.

2.9.4
You will not, directly or indirectly, display, post, disseminate, distribute, publish, broadcast, transfer, sell, or sublicense, any information provided through the Services to another individual or entity. This prohibition expressly includes "scraping" (including screen and database scraping), "data mining", or any other activity intended to collect, store, re-organize, summarize, or manipulate any information provided or any related data.

## Zillow

Zillow Group does not allow scraping nor storage of their listing data. This includes through their api, and only allows dynamic data

Q: Can we store Zillow data through the Bridge API?

A: No. You may use the API only to retrieve and display dynamic content from Zillow. You are not permitted to store information locally.

## Homes.com

Not allowed on /routes/ or /services/

from TOS:
Copyright in the Services is owned by CoStar Group, Inc, an affiliate of Homes, and the Services may only be used for informational purposes. The content displayed on the Services, including but not limited to the website’s look and feel, layout, text, graphics, images, sound or video materials, designs, the URL and software (collectively “Content”), is either the property of, or used with permission by CoStar Group, Inc. and is protected by United States and international copyright and trademark laws. All rights, including but not limited to, copyright, title and interest in the Content belong to CoStar Group, Inc. and/or its respective owners. The compilation (meaning the collection, arrangement and assembly) of all Content on the Services is also the exclusive property of CoStar and/or its respective owners and protected by U.S. and international copyright laws.

You are strictly prohibited from reproducing, republishing, copying, transmitting, distributing in any form, or by any means, any Content.

Without limiting the generality of the other restrictions set forth herein, you may not access, conduct automated queries, monitor or copy any Content or other information of the Services using any “robot”, “spider”, “deep link”, “scraper”, “crawlers”, or other automated means, methodology, algorithm or device or any manual process for any purpose.

## Movoto.com

This is a wordpress site, not sure if that has any implications...

Allowed to use Allow: /api/dosearch/, may be worth looking into. does not listing housing features...
You agree that you will not copy, reproduce, alter, modify, retransmit, redistribute decompile, disassemble, reverse engineer, or create derivative works from the Service, Site or their underlying software. You also agree not to use any automated or manual process, robot, spider or screen-scraper to copy or monitor any part of the Service. By submitting a query or otherwise reviewing the information on this website concerning real property listings (the “Data”) you agree to the following: (i)you will not access the Data through automated or high-volume means; and (ii) you will not “scrape,” harvest or otherwise copy the Data except pursuant to your personal non-commercial use of the Data solely to identify real property listings that you may be interested in investigating further.

## Estately.com

You will use the Service strictly in accordance with these Terms, all Documentation, the Privacy Policy, and Applicable Law. You will not engage in any of the following activities:
(iv) use, modify, copy, or create derivative works from the Service or Marks without the applicable owner's written permission, including without limitation using automated or manual means to access copy content from the Service;

## Homefinder.com

Among other things, you agree not to:

except with the express written permission of Teacup, modify, copy, distribute, transmit, display, perform, reproduce, publish, license, create derivative works from, frame in another Web page, use on any other Web site or application, transfer or sell any information, software, lists of users, databases or other lists, products or services provided through or obtained from the Network, including without limitation, engaging in the practices of “screen scraping,” “database scraping,” or any other activity with the purpose of obtaining lists of users or other information;

## Paid APIS

there are many paid apis that do what we want. a simple one looks like https://app.rentcast.io/app/api. brdige, corelogics, and others also exist. some lists
https://realtyna.com/mls-router-api/
https://www.realestateapi.com/
https://rapidapi.com/realtymole/api/realty-mole-property-api
https://developer.batchdata.com/docs/batchdata/batchdata-v1%2Foperations%2Fcreate-a-property-lookup-all-attribute
https://www.mlsgrid.com/resources

# Energy

Done with EIA's API.

Using EIA v2 api for electricity prices by month per state. API key is free

https://www.eia.gov/opendata/pdf/EIA-APIv2-HandsOn-Webinar-11-Jan-23.pdf
https://www.eia.gov/opendata/?category=0
https://www.eia.gov/opendata/documentation.php

# Census

https://www.census.gov/data/developers/data-sets.html

pop api:

https://www.census.gov/data/developers/data-sets/popest-popproj/popest.html

> If specified criteria are met, a metropolitan statistical area containing a single core with a population of 2.5 million or more may be subdivided to form smaller groupings of counties referred to as "metropolitan divisions."

https://www.census.gov/programs-surveys/metro-micro/about/glossary.html

https://www.nber.org/research/data/census-core-based-statistical-area-cbsa-federal-information-processing-series-fips-county-crosswalk

# Redivis

https://redivis.com/datasets/dbhp-0vj8t27f9

# Project

Metros chosen:

Minneapolis-St. Paul-Bloomington, MN-WI
Tampa-St. Petersburg-Clearwater, FL -> reevaluating
Washington-Arlington-Alexandria, DC-VA-MD-WV

# Terminology

Search page: when searching a location, this is what is displayed. Typically a map on the left with listing results on the right.

Listing page: the page showing a house's listing. Has information about the property, as well as supplemental info

Search page csv: when looking at a search page, there is a button by the pagination buttons. If there are houses on the search page, a "download all" button will appear. The contents of that link, a CSV file, are what is being referred to.

Attributes: Typically in reference to a listing attribute. These describe the listing, such as location, price, and relevant info from the listing page.

# Misc

Each house takes about 1.7 seconds averaged over the programs run time. This includes a random amount of time between .6 and 1.1 seconds

# Documentation

Documentation is done with mkdocs, mkdocstrings, mkdocs_gen_files, and mkdocs-material. To build documentation, run `mkdocs serve`. To build a static site, run `mkdocs build`, and the output will be in the sites directory.

# Output

output from running the program happens in two places, in output/, and in src/backend/.cache/. In output, there are folders with the names of metropolitans. inside are files with the name of a zip code. in these zip code files, the data collected is stored and can be retrieved. In src/backend/.cache, census data is stored. this will likely by changed to be another top level folder in output/. It will have the lookups in one folder, and outputs of our cleaned data in another folder

# Sources

Census data: DP05 and S1901 tables from the American Community Survey 5 year, vintage 2019, https://www.census.gov/data/developers/data-sets/acs-5year.html. Get your API key from: https://api.census.gov/data/key_signup.html.

Energy price data: Energy Information Administration, https://www.eia.gov/opendata/. Get your API key from the right hand side by clicking the register button

Augmenting data: This folder contains a collection of files that help with geo location information.
    * ZIP_CBSA_092023: HUD crosswalk between ZIP codes and CBSAs: https://www.huduser.gov/apps/public/uspscrosswalk/home. 
    * uszips: Contains lat/long, county name, state id, and city name, among other things: https://simplemaps.com/data/us-zips.
    * cbsa-est2022: Translation from CBSA number and its Census defined name.
    * master: inner join of some information from the above files 