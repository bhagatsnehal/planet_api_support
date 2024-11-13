# Planet API Downloader

## ABOUT
-----------------------------------------------------------------------------------------------------
This repository contains code to facilitate searching and placing orders for geotiffs using the PLANET API

**Please refer to the contents of this project if you are looking to:**

A) Establish a connection to the Planet API

B) Query Planet with search requests 

C) Place an order for an asset in Planet

D) Query status of a placed order in Planet

E) Download data corresponding to an order in Planet


## PRE-REQUISITES
-----------------------------------------------------------------------------------------------------

1. Use requirements.txt. to install necessary requirements. The code was tested on python 3.8.10.

```
$ conda create -n <name> python=3.8.10
$ conda install --file requirements.txt
```

2. Retrieve API key from Planet Account Settings and update in /src/settings/secret.properties
   > :warning: 
   > Ensure not to push your KEY details to remote.
   > /src/settings/secret.properties added to .gitignore for this reason

 3. Update /src/settings/sites.txt
    - Add a list of relevant sites(locations) to query and download data for
    - This file should contain details of one location per line
    - Expected format for locations on each line
      ```
      <UNIQUE_SITE_IDENTIFIER><\t><LATITUDE_OF_LOCATION><\t><LONGITUDE_OF_LOCATION>
      ```
  4. Modify output directory path(output_data_dir) if necessary in planet_downloader.py

## DOWNLOAD DATA
-----------------------------------------------------------------------------------------------------

Run the python_downloader.py script with necessary arguments 

```
$ python planet_downloader.py -cc 0.01 -rlat=0.05 -rlon=0.05 -start-date=20210101 -end-date=20210228
```
Details of arguments:
  - cc         : Cloud coverage as a decimal percentage
  - rlat       : Spatial distance in degrees about a latitude to create a bounding box
  - rlon       : Spatial distance in degrees about a longitude to create a bounding box
  - start-date : Start date from which to query Planet
  - end-date   : End date up to which to query Planet

## DETAILS OF PROCESS
-----------------------------------------------------------------------------------------------------

The code executes download requests in the following order:
  1. Setup authentication using API KEY
  2. Create a list of orders based on location and date ranges provided
  3. Place individual orders in batches of 100 from above list
  4. Download individual orders in batches of 100
  5. Any Client-Side/Server-Side errors in this process trigger a retry(upto maximum 3 retries)

## OUTPUT FILES GENERATED
-----------------------------------------------------------------------------------------------------

1. **log file[<my_log_date_time.log>]** with details of the script run is written to under /test/logs/*
2. **possible lit of orders[<planned_orders_<uid>.txt>]** which contains a list of attempted orders is written to /src/settings/planned_orders/*
3. **data** files are downloaded to output_data_dir : '/data/planet/'

## REFERENCES
-----------------------------------------------------------------------------------------------------
[PLANET DATA API SPEC
](https://developers.planet.com/docs/apis/data/reference/)

[PLANET ORDERS API SPEC
](https://developers.planet.com/apis/orders/reference/)


