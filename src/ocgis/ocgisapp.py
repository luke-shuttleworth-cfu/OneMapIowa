import logging
import arcgis
LOGGER = logging.getLogger(__name__)

def _website_navigation(username: str, password: str) -> str:
    pass

def _content_parsing(content: str) -> dict:
    pass

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
    def __init__(self, arcgis_username: str, arcgis_password: str, layer_url: str, onecall_username: str, onecall_password: str):
        self.arcgis_username = arcgis_username
        self.arcgis_password = arcgis_password
        self.layer_url = layer_url
        self.onecall_username = onecall_username
        self.onecall_password = onecall_password
        self._setup()
    
    def _setup(self):
        self.gis = arcgis.GIS('https://www.arcgis.com', self.arcgis_username, self.arcgis_password)
        self.layer = arcgis.features.FeatureLayer(self.layer_url, self.gis)
        
    def run(self):
        LOGGER.info('Start run')
        tickets_page_content = _website_navigation(self.onecall_username, self.onecall_password)
        # maybe convert to a needed data type
        tickets_content = [] # split content by Iowa One Call header to get list of content for eah individual ticket
        
        for ticket_content in tickets_content:
            ticket_dictionary = _content_parsing(ticket_content)
            adds, deletes, updates = _stage_changes(ticket_dictionary)
        self.layer.edit_features(adds=arcgis.features.FeatureSet(adds), updates=arcgis.features.FeatureSet(updates), deletes=arcgis.features.FeatureSet(deletes))
        
        LOGGER.info('End run')
        