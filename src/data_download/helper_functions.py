import math
import datetime


def generate_coords(lat, lon, res_lat, res_lon):
    """
    Generate a bounding box centered at the given latitude and longitude
    Args:
        lat: latitude of the location
        lon: longitude of the location
        res_lat: resolution in degrees beyond the center along the latitude
        res_lon: resolution in degrees beyond the center along the longitude

    Returns:
        Cyclic list of coordinates that represent a rectangular polygon
    """
    lon_adjustment = res_lon / math.cos(math.radians(lat))
    bounding_box = [
        [lon + lon_adjustment, lat + res_lat],
        [lon - lon_adjustment, lat + res_lat],
        [lon - lon_adjustment, lat - res_lat],
        [lon + lon_adjustment, lat - res_lat],
        [lon + lon_adjustment, lat + res_lat]
    ]
    return bounding_box


def get_locations_and_dates_to_download(start_dt, end_dt, srclist_filepath, destlist_filepath):
    """

    Args:
        start_dt:
        end_dt:
        srclist_filepath:
        destlist_filepath:

    Returns:

    """
    with open(srclist_filepath) as f:
        site_locations = f.read().splitlines()

    # Create list lat lon tuples from proposed site locations
    lats_longs = [[(site.split("\t")[0]), float(site.split("\t")[1]), float(site.split("\t")[2])] for site in
                  site_locations]

    # Create date range of 1st day of month to 15th day of month for every month in the specified time duration

    current_date = start_dt
    download_dates = []

    while current_date <= end_dt:
        # Add (start-date end-date) tuple to a list
        download_dates.append(
            (current_date.strftime("%Y-%m-%d"), (current_date + datetime.timedelta(days=15)).strftime("%Y-%m-%d")))

        current_date = current_date.replace(day=1)  # Set day to 1
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    # Create a list of order per site per date range
    orders_to_be_placed = [[site_id, lat, lon, start, end] for site_id, lat, lon in lats_longs for (start, end) in
                           download_dates]

    with open(destlist_filepath, 'w') as f:
        for order in orders_to_be_placed:
            f.write(str(order) + '\n')

    return orders_to_be_placed
