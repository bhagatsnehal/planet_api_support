import configparser
import requests
from requests.auth import HTTPBasicAuth
from retrying import retry

# Configure environment variables
config = configparser.ConfigParser()
config.read('../settings/secret.properties')

# Access a environment variables value
api_key = config.get('API', 'PL_API_KEY')
search_url = config.get('API_LINKS', 'SEARCH_URL')
place_order_url = config.get('API_LINKS', 'PLACE_ORDER_URL')
get_order_details_url = config.get('API_LINKS', 'GET_ORDER_DETAILS_URL')
# download_order_url = config.get('API_LINKS', 'DOWNLOAD_ORDER_URL')

auth = HTTPBasicAuth(api_key, '')


def create_geometry_filter(polygon_coordinates_list):
    """
    Creates a geometry filter given a polygon geometry for search requests

    Args:
        polygon_coordinates_list: polygon coordinates as a clockwise list of paired lat-long coordinates

    Returns:
        returns json object compatible to be applied as a geometry filter in a search request to Planet API
    """
    geojson_geometry = {
        "type": "Polygon",
        "coordinates": [
            polygon_coordinates_list
        ]
    }

    geom_filter = {
        "type": "GeometryFilter",
        "field_name": "geometry",
        "config": geojson_geometry
    }

    return geom_filter


def create_date_range_filter(from_date, to_date):
    """
    Creates a date range filter for search requests
    Args:
        from_date: start date for download in YYYY-MM-DD string format
        to_date: end date for download in YYYY-MM-DD string format

    Returns:
        returns json object compatible to be applied as a date range filter in a search request to Planet API
    """
    from_date = from_date + "T00:00:00.000Z"
    to_date = to_date + "T00:00:00.000Z"

    date_range_filter = {
        "type": "DateRangeFilter",
        "field_name": "acquired",
        "config": {
            "gte": from_date,
            "lte": to_date
        }
    }

    return date_range_filter


def create_cloud_cover_filter(less_than_percentage):
    """
    Creates a cloud cover filter for search requests
    Args:
        less_than_percentage: maximum acceptable percentage of cloud cover across images

    Returns:
        returns json object compatible to be applied as a cloud coverage filter in a search request to Planet API
    """
    less_than_percentage = round(less_than_percentage, 2)

    cloud_cover_filter = {
        "type": "RangeFilter",
        "field_name": "cloud_cover",
        "config": {
            "lte": less_than_percentage
        }
    }

    return cloud_cover_filter


def create_search_payload(combined_filter, item_type="PSScene"):
    """
    Creates a search payload to be passed in the quick search request
    Requires a filter that filters the search results

    Args:
        combined_filter: A dictionary containing a list of filters to filter search results by
                        {
                  "type": "AndFilter" / "OrFilter"
                  "config": [list of filters e.g. geometry, date range, cloud coverage]
              }
        item_type: type of Planet asset type reference: https://developers.planet.com/docs/apis/data/items-assets/
                default value is "PSScene"
    Returns:
        search request json to be passed in the quick search request
    """
    search_request = {
        "item_types": [item_type],
        "filter": combined_filter
    }
    return search_request

@retry(
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000)
def get_search_result(geometry_filter, date_range_filter, cloud_cover_filter):
    """
    Makes a post request to Planet API with provided search filters

    Args:
        geometry_filter: A geometry filter with polygon coordinates
        date_range_filter: A date range filter with gte(greater than equal) and lte(less than equal) dates
        cloud_cover_filter: A cloud coverage filter with max acceptable percentage of cloud cover

    Returns:
        Returns complete metadata objects about the items(images+metadata) matching search criteria
    """
    combined_filter = {
        "type": "AndFilter",
        "config": [geometry_filter, date_range_filter, cloud_cover_filter]
    }
    search_request = create_search_payload(combined_filter)
    search_result = requests.post(
        search_url,
        auth=HTTPBasicAuth(api_key, ''),
        json=search_request)

    if search_result.status_code == 429:
        raise Exception("rate limit error, will attempt retry")

    return search_result


@retry(
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000)
def place_order(image_id, polygon_coords, order_name_suffix, crs_system="EPSG:4326"):
    """
    Sends order requests for specified image asset id to be clipped to the specified polygon coordinate window
    Args:
        image_id: image id to be downloaded
        polygon_coords: polygon coordinate bound/window to clip the image id to
        order_name_suffix: order name suffix to be appended as an identifier for the order
        crs_system: coordinate reference system to convert the returned image to

    Returns:
        result details of order placed, most notably the unique order id created for the order

    """
    order_request = {
        # "name": image_id + order_name_suffix,
        "source_type": "scenes",
        "products": [
            {
                "item_ids": [
                    image_id
                ],
                "item_type": "PSScene",
                "product_bundle": "visual"
            }
        ],
        "tools": [
            {
                "clip": {
                    "aoi": {
                        "type": "Polygon",
                        "coordinates": [
                            polygon_coords
                        ]
                    }
                }
            }
        ]
    }

    order_result = requests.post(
        place_order_url,
        auth=HTTPBasicAuth(api_key, ''),
        json=order_request)

    if order_result.status_code == 429:
        raise Exception("rate limit error, will attempt retry")

    return order_result


@retry(
    wait_exponential_multiplier=1000,
    wait_exponential_max=10000)
def get_order_status(order_id):
    """
    Get the status and results of a placed order
    Args:
        order_id: unique order identifier

    Returns:
        the response from get request: includes the original order request and timestamp, order state, error hints,
            last message, last update timestamp of the order
    """
    order_details = requests.get(
        get_order_details_url.format(order_id),
        auth=HTTPBasicAuth(api_key, '')
    )

    if order_details.status_code == 429:
        raise Exception("rate limit error, will attempt retry")

    return order_details


def download_order(download_order_url):
    """
    Download the asset pointed at by the download url
    Args:
        download_order_url: download link for an asset(either image/metadata file)

    Returns:
        returns download result containing status code and file content
    """
    order_details = requests.get(
        download_order_url,
        auth=HTTPBasicAuth(api_key, '')
    )

    if order_details.status_code == 429:
        raise Exception("rate limit error, will attempt retry")

    return order_details






