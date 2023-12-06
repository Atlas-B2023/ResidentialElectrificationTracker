# DISCLAIMER

Utilizing Redfin's data for commercial use is prohibited. MLS data may be protected by copyright laws. Program authors do not take responsibility for any action Redfin or its MLS brokers take against users of this software. Redfin data is not prepackaged in this repository. 

(Not sure if we need a license file? Consider as source available, and free to modify, and not free to sell)

# Installation Directions

1. Download Python 3.12 from the [official website](https://www.python.org/downloads/) (the big button usually works).
2. Download this repository, either by cloning or by downloading the ZIP file.
3. Run the included `setup.bat`.
4. Thats it!

The installation steps are covered in the YouTube video series on the documentation page as well.

# How to Run the program

In order to run this program, two API keys are required. The instructions on how to get these are listed in the [Energy](#energy) and [Census](#census) sections.

Once these have been acquired, create a file named `.env` in the `src\` folder.

In this file, write `CENSUS_API_KEY=` and `EIA_API_KEY=` on the first two lines, and after the equals sign paste in your key for each entry.

To start the application, double click on the `run.bat` file. This should start the application, and now you can use it!

# Paid APIS

There are many paid APIs allow commercial use.

- [RealestateAPI](https://www.realestateapi.com/)
- [RealtyNA](https://realtyna.com/mls-router-api/)
  - Has plans for access + MLS fees.
- [Rentcast](https://app.rentcast.io/app/api)
- [Bridge](https://www.bridgeinteractive.com/developers/zillow-group-data/)
  - Does not allow local storage of data.
- [Corelogic](https://www.corelogic.com/data-solutions/property-data-solutions/)
- [RealtyMole](https://rapidapi.com/realtymole/api/realty-mole-property-api)
- [BatchData](https://developer.batchdata.com/docs/batchdata/batchdata-v1%2Foperations%2Fcreate-a-property-lookup-all-attribute)
- [MLSGrid](https://www.mlsgrid.com/resources)

# Energy

Energy prices are through the EIA's open data API.

Get your API key here: https://www.eia.gov/opendata/register.php

https://www.eia.gov/opendata/pdf/EIA-APIv2-HandsOn-Webinar-11-Jan-23.pdf
https://www.eia.gov/opendata/?category=0
https://www.eia.gov/opendata/documentation.php

# Census

Census data is collected through their API. We use the ACS 5 year profile and subject tables DP05 and S1901, respectively.

> If specified criteria are met, a metropolitan statistical area containing a single core with a population of 2.5 million or more may be subdivided to form smaller groupings of counties referred to as "metropolitan divisions."

Get your API key here: https://api.census.gov/data/key_signup.html

https://www.census.gov/programs-surveys/metro-micro/about/glossary.html

https://www.nber.org/research/data/census-core-based-statistical-area-cbsa-federal-information-processing-series-fips-county-crosswalk

# Misc

Each request from Redfin takes about 4.5 seconds to GET and analyze. This is intentional so as to not flood Redfin's servers.

# Output

Output is organized as such:

```
output/
├── metro_data/
│   ├── <Metro_name>/
│       ├── <zip>.csv
│   ├── <Other_metro_name>/
│       ├── <otherzip>.csv
├── census_data/
│   ├── cache/
│       ├── <chache>.json
│   ├── <acs5>.csv
├── logging/
│     ├── logging.log
```

> [!WARNING]
> If you are running metros that share zip codes, the same zip code will be imported twice. This is an improvement that can be done by checking what zip codes have been loaded in the sister repository.

# Sources

Census data:

> DP05 and S1901 tables from the American Community Survey 5 year, vintage 2019, https://www.census.gov/data/developers/data-sets/acs-5year.html.

> Get your API key from: https://api.census.gov/data/key_signup.html.

Energy price data:

> Energy Information Administration, https://www.eia.gov/opendata/.

> Get your API key from the right hand side by clicking the register button

Augmenting data:

> This folder contains a collection of files that help with geo location information.

- `ZIP_CBSA_092023`: HUD crosswalk between ZIP codes and CBSAs: https://www.huduser.gov/apps/public/uspscrosswalk/home.
- `uszips`: Contains lat/long, county name, state id, and city name, among other things: https://simplemaps.com/data/us-zips.
- `cbsa-est2022`: Translation from CBSA number and its Census defined name.
- `master`: inner join of some information from the above files

Housing data:

> Redfin's stingray API

# Improvements

Create a fully python app. Plotly has native python support for all things spacial analysis. https://plotly.com/python/mapbox-county-choropleth/. Additionally, using Dash https://dash.plotly.com/ might make the experience more seamless

Add tool bar for graphs. Use mplcursors for hover on the graph.

Use census library from python: acs5dp and acs5st

Use database to store information, and implement caching/purging (if TOS allows)

Remove duplicate zip code placements due to zip codes being in multiple metropolitan areas
