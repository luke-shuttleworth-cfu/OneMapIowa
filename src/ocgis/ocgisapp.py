import logging
import arcgis
from lxml import html
import re
from .attribute_maps import NEW_ATTRIBUTE_MAP
from datetime import datetime
from bs4 import BeautifulSoup
LOGGER = logging.getLogger(__name__)

DATE_FORMAT = '%m/%d/%y %I:%M %p'

def _website_navigation(username: str, password: str) -> str:
    pass

def convert_geometry_rings(coordinates):
    """Converts latitude/longitude coordinates to webmercator projection.

    Args:
        coordinates (list): List containing lists of points, potentially for multiple
        geometries - e.g. [[[x1, y1], [x2, y2]], [[a1, b1], [a2, b2]]]

    Returns:
        list: List containing lists of points, potentially for multiple
        geometries - e.g. [[[x1, y1], [x2, y2]], [[a1, b1], [a2, b2]]]
    """
    final_points = []
    for polygon in coordinates:
        webmercator_points = []
        for lat, lon in polygon:
            # Create a Point geometry with WGS84 coordinates
            wgs_point = arcgis.geometry.Point(
                {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}})
            # Project the point to Web Mercator (wkid 3857)
            webmercator_point = wgs_point.project_as(arcgis.geometry.SpatialReference(3857))

            webmercator_points.append(
                [webmercator_point.x, webmercator_point.y])
        final_points.append(webmercator_points)
    return final_points

def _content_parsing(html_content: str, attribute_map: dict, districts: list, closed_statuses: list, dictionary_format: dict, spatial_reference: int) -> dict:
    # Function to find a table by headers using partial matching
    def _find_table_by_headers(tree, target_headers):
        for table in tree.xpath('//table'):
            # Extract headers of the current table
            headers = set(table.xpath('.//th/text()'))
            # Check if all target headers are contained within the table's headers
            if target_headers.issubset(headers):
                # Convert table to a list of dictionaries
                headers = table.xpath('.//th/text()')  # Re-fetch headers to maintain order
                table_data = []
                for row in table.xpath('.//tbody/tr'):
                    cells = row.xpath('td/text()')
                    row_dict = dict(zip(headers, cells))
                    table_data.append(row_dict)
                return table_data
        LOGGER.debug(f"No table found for headers '{target_headers}'.")
        return None
    
    tree = html.fromstring(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    
    # ----- Get attribute data -----
    attributes = {}
    
    
    # Get value for each attribute in the attribute map using the xpaths
    for attribute, identifier in attribute_map.items():
        try:
            content = tree.xpath(f'{identifier}/text()')
            if identifier:
                if type(content) == list and len(content) > 0:
                    content = content[0]
                else:
                    content = ''
                attributes[attribute] = re.sub(r'\s+', ' ', content).strip()
            else:
                LOGGER.debug(f"No xpath expression for '{attribute}'.")
        except Exception:
            LOGGER.exception(f"Error finding value for '{attribute}'")
    
    
    
    # ----- Get statuses -----
    
    target_headers = {'District', 'Company Name', 'Status'}
    status_dictionary = _find_table_by_headers(tree, target_headers)
    
    ticket_open = False
    # Check statuses, if any are still open mark ticket as opened and if CFU then update attributes.
    for status_row in status_dictionary:
        if status_row['District'].lower() in districts:
            attributes[status_row['District'].lower()] = status_row['Status']
        if status_row['Status'] not in closed_statuses:
            ticket_open = True
        
    if ticket_open:
        attributes['status'] = 'OPEN'
    else:
        attributes['status'] = 'CLOSED'
        
    
    
    
    # ----- Get polygon information -----
    
    # Find all divs with class "pure-u-md-1-1" containing polygon headers
    polygon_headers = soup.find_all('div', class_='pure-u-md-1-1')
    geometry_rings= []
    # Iterate through each polygon header
    for header in polygon_headers:
        polygon_data = []
        # Find the <b> tag within the header
        polygon_number_tag = header.find('b')
        if polygon_number_tag:
            # Get the polygon number from the <b> tag text
            polygon_number = polygon_number_tag.text.strip().replace(':', '')

            # Find all following divs until the next polygon header or end of parent div
            next_element = header.find_next_sibling()
            # stop when next header is found
            while next_element and not next_element.find('b', string=True):
                if next_element.name == 'div' and 'pure-u-md-1-3' in next_element['class']:
                    text = next_element.get_text().strip()
                    if text.startswith('(') and text.endswith(')'):
                        # Remove parentheses and split by comma
                        coordinates = text[1:-1].strip().split(',')
                        # Convert to float and append to polygon_data
                        polygon_data.append([float(coord.strip())
                                            for coord in coordinates])
                next_element = next_element.find_next_sibling()

            # Append polygon_data to all_polygons if it has any points
            if polygon_data:
                geometry_rings.append(polygon_data)
    
    
    # ----- Return dictionary -----
    
    attributes['lastAutomaticUpdate'] = datetime.now().strftime(DATE_FORMAT)

    dictionary_format['attributes'] = attributes
    dictionary_format['geometry']['rings'] = convert_geometry_rings(geometry_rings)
    return dictionary_format
    

def _stage_changes(ticket_dictionary: dict, layer: arcgis.features.FeatureLayer) -> dict:
    """
    Stage changes for a ticket by determining whether it should be added, updated, or deleted in the feature layer.

    Args:
        ticket_dictionary (dict): A dictionary representing a ticket, which should contain:
            - 'attributes': A dictionary of feature attributes, including 'ticketNumber'.
            - 'geometry': A dictionary defining the feature's geometry.
        layer (arcgis.features.FeatureLayer): The feature layer to check for the existence of the ticket.

    Returns:
        tuple[list, list, list]: A tuple containing three lists:
            - adds (list): A list of `arcgis.features.Feature` objects to be added.
            - deletes (list): A list of `arcgis.features.Feature` objects to be deleted.
            - updates (list): A list of `arcgis.features.Feature` objects to be updated.

    Raises:
        KeyError: If 'ticketNumber' is not found in the 'attributes' of `ticket_dictionary`.
        Exception: If any unexpected error occurs during the execution of the function.

    Notes:
        - The function checks if the feature already exists in any of the lists (`adds`, `deletes`, `updates`).
        - If the feature exists in the layer (determined by `_ticket_exists`), it is added to the `updates` list.
        - If the feature does not exist in the layer, it is added to the `adds` list.
        - The function uses a `try` block to handle exceptions and logs errors using `LOGGER`.
    """
    try:
        ticket_number = ticket_dictionary['attributes']['ticketNumber']
        # Create feature
        feature = arcgis.features.Feature(ticket_dictionary['geometry'], ticket_dictionary['attributes'])
        
        adds, deletes, updates = [], [], []
        if feature in adds or feature in deletes or feature in updates:
            LOGGER.info(f"Duplicate ticket '{ticket_number}' found.")
        elif _ticket_exists(layer, ticket_number):
            updates.append(feature)
            LOGGER.info(f"Update ticket '{ticket_number}'.")
        else:
            adds.append(feature)
            LOGGER.info(f"Add ticket '{ticket_number}'.")
        
        return adds, deletes, updates
    except KeyError:
        LOGGER.exception(f"KeyError: 'ticketNumber' is missing from ticket dictionary.")
        raise


def _ticket_exists(layer: arcgis.features.FeatureLayer, ticket_number: str) -> bool:
    """
    Check if a ticket (feature) with the specified object_id exists in the given FeatureLayer.

    Args:
        layer (FeatureLayer): The ArcGIS FeatureLayer object to query.
        object_id (str): The ID of the feature to check for existence.

    Returns:
        bool: True if the feature exists, False otherwise.
    """
    try:
        # Query the FeatureLayer for the specific object_id
        query = f"ticketNumber = {ticket_number}"
        result = layer.query(where=query, return_count_only=True)

        # Check if the feature count is greater than 0
        return result > 0
    except Exception as e:
        # Log the error or handle it as needed
        LOGGER.exception(f"Error querying FeatureLayer for ticket number {ticket_number}.")
        return False

def _object_id_from_ticket_number(ticket_number: str | int, layer: arcgis.features.FeatureLayer) -> str:
    """
    Convert a ticket number (which can be a string or an integer) to an object ID.

    Args:
        ticket_number (str | int): The ticket number to convert.
        layer (FeatureLayer): The ArcGIS FeatureLayer object to query.

    Returns:
        str: The corresponding object ID.

    Raises:
        ValueError: If ticket_number cannot be processed into a valid object ID.
    """
    try:
        # Ensure ticket_number is a string
        if isinstance(ticket_number, int):
            ticket_number = str(ticket_number)
        elif not isinstance(ticket_number, str):
            raise TypeError("ticket_number must be a string or integer.")
        
        # Validate the ticket_number format (if needed)
        if not ticket_number.isdigit():
            raise ValueError("ticket_number must contain only digits.")
        
        # Query the FeatureLayer for the object ID
        query = f"ticket_number_field = '{ticket_number}'"  # Replace 'ticket_number_field' with the actual field name in your layer
        result = layer.query(where=query, return_fields="OBJECTID", return_count_only=False)

        # Check if any features are found
        if result.features:
            # Assuming the first feature contains the object ID
            object_id = result.features[0].attributes["OBJECTID"]
            return str(object_id)
        else:
            raise ValueError(f"No object found for ticket number '{ticket_number}'.")

    except (TypeError, ValueError) as e:
        LOGGER.exception(f"An error occurred getting the object ID for ticket '{ticket_number}': {e}")
        raise
    except Exception as e:
        LOGGER.exception(f"An unexpected error occurred: {e}")
        raise



class OcGisApp:
    def __init__(self, arcgis_username: str, arcgis_password: str, layer_url: str, onecall_username: str, onecall_password: str, districts: list, closed_statuses=["Closed, Marked"]):
        self.arcgis_username = arcgis_username
        self.arcgis_password = arcgis_password
        self.layer_url = layer_url
        self.onecall_username = onecall_username
        self.onecall_password = onecall_password
        self.closed_statuses = closed_statuses
        self.districts = districts
        self._setup()
    
    def _setup(self):
        self.gis = arcgis.GIS('https://www.arcgis.com', self.arcgis_username, self.arcgis_password)
        self.layer = arcgis.features.FeatureLayer(self.layer_url, self.gis)
        self.spatial_reference = self.layer.properties['extent']['spatialReference']['wkid']
        self.feature_dictionary = {
            'attributes': None,
            'geometry': {
                "rings": None,
                "spatialReference": {
                    # Example WKID for Web Mercator (WGS84)
                    "wkid": self.spatial_reference,
                    "latestWkid": self.layer.properties['extent']['spatialReference']['latestWkid']
                }
            }
        }
        
    def run(self):
        LOGGER.info('Start run.')
        tickets_page_content = _website_navigation(self.onecall_username, self.onecall_password)
        # maybe convert to a needed data type
        tickets_content = [] # split content by Iowa One Call header to get list of content for eah individual ticket
        
        for ticket_content in tickets_content:
            ticket_dictionary = _content_parsing(ticket_content)
            adds, deletes, updates = _stage_changes(ticket_dictionary)
        self.layer.edit_features(adds=arcgis.features.FeatureSet(adds), updates=arcgis.features.FeatureSet(updates), deletes=arcgis.features.FeatureSet(deletes))
        
        remaining_open_tickets = self.layer.query(where="status = 'OPEN'")
        
        LOGGER.info('End run.')
        
        
    def test(self, string):
        LOGGER.debug('Start test')
        
        for key, attribute in _content_parsing(string, NEW_ATTRIBUTE_MAP, self.districts, self.closed_statuses, self.feature_dictionary, self.spatial_reference).items():
            if(key != 'geometry'):
                print(f'{key}: {attribute}')
        
        LOGGER.debug('End test')
        