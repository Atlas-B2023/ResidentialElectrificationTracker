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

Currently respects robots.txt. Looking into what /*/amp? is

## HAR Files

In order to get sold listings, you must zoom in on the map and save a har file of the network.

The file to analyze is similar to https://www.redfin.com/stingray/api/gis/avm?al=1&poly=-117.69722%2034.09242%2C-117.69516%2034.09242%2C-117.69516%2034.09374%2C-117.69722%2034.09374%2C-117.69722%2034.09242&v=8, and is started by "{}&&{"version":502,"errorMessage":"Success","resultCode":0,"payload":{"homes":[{"mlsId":{"label":"MLS#"" Since panning can create intersecting listings,
the entry and connections should be limited to new listings not seen before

# Storage

Storage is handled in a local database. Currently looking at SQLite (sqlite3). It has the following schema:

> {address, zipcode, yearbuilt, price, sqft, heatingtype}

### Considerations of elements of schema

price: This will be the last sold price. If a house has not been sold yet, it will be the list price. Since Redfin's estimate is made through machine learning, we would like to not use it. If need be, the property tax valuation of the home is listed, and can be used. 

yearbuilt: since we are only collecting recent data, and since we can filter by year built through Redfin, this will be the value. Last selling year is not a useful metric so it is not included in our schema.

heatingtype: this can take many forms. Some houses are hybrid, some have limited information available. Here is a non exhaustive list of some English found for heating system descriptions

> Baseboard Heat, Hot Water, Multi-Zone Heat; Heat Fuel: Propane; Water Heater Off Heating System, On Demand Water Heater, Tankless Water Heater

*Note: Baseboard heat comes in two styles, electric and heated water. This case seems to be heated water.*

> Heating: Central

> Heating: Forced Air

> Heating: Heat pump

> Heating: Electric

> Heating: Natural Gas

> Air Conditioning Type: Central;
Heating Type: Central

>Cooling: Mini Split; Heat: Radiator, Steam, Mini Split; Heat Fuel: Oil

# Energy

[WattBuy](https://wattbuy.com/en/) seems to have information on costs. look at [api](https://wattbuy.readme.io/reference/creating-an-account). "You are restricted from caching Licensed Content or any other output of WattB's APIs." Probably should just use [OpenEI](https://apps.openei.org/USURDB/).