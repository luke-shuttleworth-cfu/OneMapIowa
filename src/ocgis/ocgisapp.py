import logging
import arcgis
from lxml import html
import re
from .attribute_maps import NEW_ATTRIBUTE_MAP
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time

LOGGER = logging.getLogger(__name__)

DATE_FORMAT = '%m/%d/%y %I:%M %p'

def _website_navigation(driver: webdriver.Edge, username: str, password: str, login_url: str, update_range: int) -> str:
    """Navigate to legacy site page to get ticket data.

    Returns:
        str: html content of website.
    """    

    driver.get(login_url)
    driver.find_element(
        By.XPATH, '//*[@id="username"]').send_keys(username)
    driver.find_element(
        By.XPATH, '//*[@name="password"]').send_keys(password)
    driver.find_element(By.XPATH, '//*[@id="btn-login"]').click()
    driver.get("https://ia.itic.occinc.com/legacyApplication")
    driver.get("https://ia.itic.occinc.com/iarecApp/servlet/Login?enc=zyfGx9MlUXnIWnwgDj%2BZiRogVJ1R215Lv3ldmSL6HqerScjlqNXM0NfCofWhgsBA%2F8v3Qc%2FybibEMwaN%2Bu%2F3ZhhiUzpdbS0s7pzIDYWfZIrbNxpPaE0LctfqPuWZ%2FVUn")

    textbox = driver.find_element(By.XPATH, '//input[@id="auditStartDate"]')
    textbox.clear()
    textbox.send_keys((datetime.now(
    ) - timedelta(days=update_range)).strftime('%Y-%m-%d'))
    textbox = driver.find_element(By.XPATH, '//input[@id="auditEndDate"]')
    textbox.clear()
    textbox.send_keys(datetime.now().strftime('%Y-%m-%d'))
    # Click ticket search button
    driver.find_element(By.XPATH, '//input[@value="Show Tickets"]').click()

    driver.execute_script("javascript:popupTktInfo('printTickets.jsp')")
    main_window = driver.current_window_handle

    # Get handles of all open windows
    all_windows = driver.window_handles

    # Switch to the new window (assuming it is the second one)
    for window in all_windows:
        if window != main_window:
            driver.switch_to.window(window)
            break
    tickets_content = driver.page_source
    return tickets_content

def _single_ticket_lookup(driver: webdriver.Edge, ticket_number: int, state: str) -> str:
    driver.get("https://ia.itic.occinc.com/iarecApp/ticketSearchAndStatusSelector.jsp")
    
    textbox = driver.find_element(By.XPATH, '//input[@id="ticketNumber"]')
    textbox.clear()
    textbox.send_keys(str(ticket_number))
    
    Select(driver.find_element(By.XPATH, '//select[@name="db"]')).select_by_visible_text(state)
    
    driver.find_element(By.XPATH, '//*[@name="Search"]').click()
    driver.execute_script('window.matchMedia("print").matches = true;')
    return driver.page_source
    
    
    
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
                #LOGGER.debug(f"No xpath expression for '{attribute}'.")
                pass
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
    
def _stage_changes(ticket_dictionary: dict, layer: arcgis.features.FeatureLayer, adds: list, deletes: list, updates: list):
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
        
        if feature in adds or feature in deletes or feature in updates:
            LOGGER.info(f"Duplicate ticket '{ticket_number}' found.")
        elif _ticket_exists(layer, ticket_number):
            feature.attributes['OBJECTID'] = _object_id_from_ticket_number(feature.attributes['ticketNumber'], layer)
            updates.append(feature)
            LOGGER.info(f"Update ticket '{ticket_number}'.")
        else:
            adds.append(feature)
            LOGGER.info(f"Add ticket '{ticket_number}'.")
        
        
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
        elif not isinstance(ticket_number, str) and not isinstance(ticket_number, int):
            raise TypeError("ticket_number must be a string or integer.")
        
        # Validate the ticket_number format (if needed)
        if not ticket_number.isdigit():
            raise ValueError("ticket_number must contain only digits.")
        
        # Query the FeatureLayer for the object ID
        query = f"ticketNumber = '{ticket_number}'"  # Replace 'ticket_number_field' with the actual field name in your layer
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
    def __init__(self, arcgis_username: str, arcgis_password: str, arcgis_link: str, layer_url: str, onecall_username: str, onecall_password: str, onecall_login_url: str, districts: list, driver_executable_path: str, update_range: int, state: str, headless=False, closed_statuses=["Closed, Marked"]):
        self.arcgis_username = arcgis_username
        self.arcgis_password = arcgis_password
        self.arcgis_link = arcgis_link
        self.layer_url = layer_url
        self.onecall_username = onecall_username
        self.onecall_password = onecall_password
        self.closed_statuses = closed_statuses
        self.districts = districts
        self.onecall_login_url = onecall_login_url
        self.update_range = update_range
        self.state = state
        self.headless = headless
        self.driver_executable_path = driver_executable_path
        self._setup()
    
      
        
    
    def _setup(self):
        
        # ----- Set up arcgis -----
        self.gis = arcgis.GIS(self.arcgis_link, self.arcgis_username, self.arcgis_password)
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
        
        # ----- Set up webdriver -----
        driver_options = Options()
        if self.headless:
            driver_options.add_argument('--headless')
        driver_options.add_argument('--log-level=3')
        driver_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        #driver_options.add_argument("--kiosk-printing")
        driver_service = Service(executable_path=self.driver_executable_path)
        self.webdriver = webdriver.Edge(options=driver_options,
                                service=driver_service, keep_alive=True)
        self.webdriver.implicitly_wait(20)
        
        # ----- Get current list from locator page -----
        
        tickets_page_content = _website_navigation(driver=self.webdriver, username=self.onecall_username, password=self.onecall_password, login_url=self.onecall_login_url, update_range=self.update_range)
        # maybe convert to a needed data type here
        tickets_content = tickets_page_content.split('<h1 style="text-align:center;">Iowa One Call</h1>')[1:]
        
        
        edited_tickets = []
        adds, deletes, updates = [], [], []
        for ticket_content in tickets_content:
            ticket_dictionary = _content_parsing(html_content=ticket_content, 
                                                 attribute_map=NEW_ATTRIBUTE_MAP, 
                                                 districts=self.districts, 
                                                 dictionary_format=self.feature_dictionary,
                                                 spatial_reference=self.spatial_reference,
                                                 closed_statuses=self.closed_statuses)
            edited_tickets.append(ticket_dictionary['attributes']['ticketNumber'])
            _stage_changes(ticket_dictionary=ticket_dictionary, layer=self.layer, adds=adds, deletes=deletes, updates=updates)
        result = self.layer.edit_features(adds=adds, updates=updates, deletes=deletes)
        LOGGER.info(f"Site edit results: adds: {len(result['addResults'])}, updates: {len(result['updateResults'])}, deletes: {len(result['deleteResults'])}")

        # ----- Check remaining open tickets -----
        
        # Construct the WHERE clause
        excluded_ticket_numbers_str = "', '".join(edited_tickets)
        where_clause = f"status = 'OPEN' AND ticketNumber NOT IN ('{excluded_ticket_numbers_str}')"
        
        remaining_open_tickets = self.layer.query(where=where_clause)
        LOGGER.debug(f"Remaining open tickets: {len(remaining_open_tickets)}.")
        
        adds, deletes, updates = [], [], []
        for ticket in remaining_open_tickets.features:
            ticket_number = ticket.attributes['ticketNumber']
            html_content = _single_ticket_lookup(self.webdriver, ticket_number, self.state)
            ticket_dictionary = _content_parsing(html_content, NEW_ATTRIBUTE_MAP, self.districts, self.closed_statuses, self.feature_dictionary, self.spatial_reference)
            _stage_changes(ticket_dictionary, self.layer, adds, deletes, updates)
        result = self.layer.edit_features(adds, updates, deletes)
        LOGGER.info(f"Open edit results: adds: {len(result['addResults'])}, updates: {len(result['updateResults'])}, deletes: {len(result['deleteResults'])}")
        self.webdriver.quit()
        LOGGER.info('End run.')
        
        
    def test(self):
        LOGGER.debug('Start test')
        
        where_clause = f"status = 'OPEN'"
        
        remaining_open_tickets = self.layer.query(where=where_clause)
        LOGGER.debug(f"Remaining open tickets: {len(remaining_open_tickets)}.")
        
        adds, deletes, updates = [], [], []
        for ticket in remaining_open_tickets.features:
            ticket_number = ticket.attributes['ticketNumber']
            html_content = _single_ticket_lookup(self.webdriver, ticket_number, self.state)
            ticket_dictionary = _content_parsing(html_content, NEW_ATTRIBUTE_MAP, self.districts, self.closed_statuses, self.feature_dictionary, self.spatial_reference)
            print(ticket_dictionary)
            _stage_changes(ticket_dictionary, self.layer, adds, deletes, updates)
        result = self.layer.edit_features(adds, updates, deletes)
        LOGGER.info(f"Open edit results: adds: {len(result['addResults'])}, updates: {len(result['updateResults'])}, deletes: {len(result['deleteResults'])}")
        
        self.webdriver.quit()
        
        LOGGER.debug('End test')
        