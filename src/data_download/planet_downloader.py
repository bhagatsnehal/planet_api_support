import argparse
import logging
import os

from os.path import join, isdir
from os import mkdir

import time
from datetime import datetime

from retrying import retry
from requests.exceptions import HTTPError

import planet_download_interface as planet
import helper_functions as helper

################################################################################

# File Logger
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)
timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
log_file = f"../../test/logs/my_log_{timestamp}.log"
handler = logging.FileHandler(log_file)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


################################################################################
def place_orders(orders_list):
    placed_orders = []

    logger.info("Placing {} orders".format(len(orders_list)))

    for site_id, lat, lon, start, end in orders_list:
        try:
            image_id, order_id = place_single_order(site_id, lat, lon, start, end)
            if image_id is not None and order_id is not None:
                placed_orders.append((image_id, order_id))
        except FileNotFoundError as f:
            logger.error("Images Unavailable - Skipped order ['{}', {}, {}, '{}', '{}']".format(site_id, lat, lon, start, end))
        except HTTPError as e:
            logger.error("Unexpected Error {} - Skipped order ['{}', {}, {}, '{}', '{}']".format(e, site_id, lat, lon, start, end))
        time.sleep(2)

    return placed_orders


@retry(stop_max_attempt_number=3, retry_on_exception=lambda e: isinstance(e, HTTPError))
def place_single_order(site_id, lat, lon, start, end):
    logger.info('Latitude:{} Longitude:{} Start Date:{} End Date:{}'.format(lat, lon, start, end))
    polygon_coords = helper.generate_coords(lat, lon, args.res_lat, args.res_lon)

    search_result = planet.get_search_result(planet.create_geometry_filter(polygon_coords),
                                             planet.create_date_range_filter(start, end),
                                             planet.create_cloud_cover_filter(args.max_cloud_coverage))

    # raise HTTPError if status not 200
    search_result.raise_for_status()

    # sleep for 1 sec before placing orders - rate limiting buffer
    time.sleep(1)

    image_ids = [feature['id'] for feature in search_result.json()['features']]
    if len(image_ids) == 0:
        logger.debug('Images unavailable for {}'.format(str(lat) + "_" + str(lon) + "_" + site_id))
        raise FileNotFoundError

    logger.info('{} images available for download'.format(len(image_ids)))
    image_id = image_ids[0]
    order_result = planet.place_order(image_id, polygon_coords,
                                      "#" + str(lat) + "_" + str(lon) + "_" + site_id)

    # raise HTTPError if status not 202
    order_result.raise_for_status()

    order_id = order_result.json().get("id")

    logger.info(
        'Order placed for {}'.format(str(image_id) + "#" + str(lat) + "_" + str(lon) + "_" + site_id + "\t" + str(
            order_id)))

    custom_image_id = str(image_id) + "#" + str(lat) + "_" + str(lon) + "_" + site_id
    return custom_image_id, order_id


################################################################################
def process_orders(placed_orders, dest_folder):
    logger.info("Initiating download for {} orders".format(len(placed_orders)))

    for image_id, order_id in placed_orders:
        try:
            process_single_order(image_id, order_id, dest_folder)
        except HTTPError as e:
            logger.error("Failed to download data for {} : {}.".format(image_id, e))


@retry(stop_max_attempt_number=3, retry_on_exception=lambda e: isinstance(e, HTTPError))
def process_single_order(image_id, order_id, dest_folder):
    # image sub folder nameing convention
    folder_name = image_id.split("#")[1]
    prefix = image_id.split("#")[0]
    logger.info(prefix)

    # Download request
    order_request_result = planet.get_order_status(order_id)
    order_request_result.raise_for_status()

    order_status = order_request_result.json()["state"]

    if order_status == "success":
        logger.info("Image {} is ready. Downloading...".format(image_id))

        outdir = join(dest_folder, folder_name)
        if not isdir(outdir):
            logger.info("Creating output sub folder {}...".format(outdir))
            mkdir(outdir)

        # Every download order returns 3 files - main tif, metadata.json and manifest.json
        for element in order_request_result.json()["_links"]["results"]:
            download_url = element["location"]
            logger.info(element["name"])
            file_name = element["name"].split("/")[-1]
            logger.info(file_name)

            # to avoid overwriting manifest files
            if file_name == "manifest.json":
                file_name = prefix + "_" + file_name

            download_result = planet.download_order(download_url)
            if download_result.status_code != 200:
                logger.error("")
            with open(join(outdir, file_name), "wb") as f:
                f.write(download_result.content)
            time.sleep(2)
        logger.info("Image {} download complete.".format(image_id))
    elif order_status in ["queued", "running"]:
        logger.info("Still processing {}. Waiting...".format(image_id))
        time.sleep(60)  # Wait 60 seconds before checking again
    else:
        logger.debug("Unexpected status {} for {}.".format(order_status, image_id))
        raise HTTPError("Unexpected order status {}".format(order_status))




################################################################################
def download_data(output_data_dir, start_dt, end_dt):
    uid = datetime.now().strftime('%Y%m%d%H%M')
    sites_list_filepath = '../settings/sites.txt'

    planned_orders_filepath = '../settings/planned_orders/planned_orders_{}.txt'.format(uid)

    orders_to_be_placed = helper.get_locations_and_dates_to_download(start_dt, end_dt,
                                                                     sites_list_filepath,
                                                                     planned_orders_filepath)

    for index in range(0, len(orders_to_be_placed), 100):
        orders_list = orders_to_be_placed[index:index + 100]

        # Place 100 orders at a time
        placed_orders = place_orders(orders_list)

        # Download last 100 placed orders to output dir
        process_orders(placed_orders, output_data_dir)


################################################################################
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--max-cloud-coverage',
                        '-cc', default=0.4, type=float,
                        help="maximum cloud coverage in percentage")
    parser.add_argument('--res-lat',
                        '-rlat', default=0.005, type=float,
                        help="resolution in degrees along the latitude axis")
    parser.add_argument('--res-lon',
                        '-rlon', default=0.005, type=float,
                        help="resolution in degrees along the longitude axis")
    parser.add_argument('--start-date',
                        '-start-date', default='20210101',
                        help="start date in YYYYMMDD format for date range filter")
    parser.add_argument('--end-date',
                        '-end-date', default='20210101',
                        help="end date in YYYYMMDD format for date range filter")
    args = parser.parse_args()

    format_data = "%Y%m%d"

    logger.info("Starting download process now.....")
    try:
        start_date = datetime.strptime(args.start_date, format_data)
        end_date = datetime.strptime(args.end_date, format_data)
    except ValueError as e:
        logger.error("Input start/end date not in expected format YYYYMMDD:", e)

    output_data_dir = '../../data/planet/'

    if not os.path.exists(output_data_dir):
        os.makedirs(output_data_dir)

    download_data(output_data_dir, start_date, end_date)
    logger.error("Download Process Complete")
