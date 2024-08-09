import logging
import arcgis
LOGGER = logging.getLogger(__name__)

def _website_navigation(username: str, password: str) -> str:
    pass

def _content_parsing(content: str) -> dict:
    pass

def _push_to_map(content: dict) -> dict:
    pass

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

def _object_id_from_ticket_number(ticket_number: str | int) -> str:
    """
    Convert a ticket number (which can be a string or an integer) to an object ID.

    Args:
        ticket_number (str | int): The ticket number to convert.

    Returns:
        str: The corresponding object ID.
    """
    try:
        # Ensure ticket_number is a string
        if isinstance(ticket_number, int):
            ticket_number = str(ticket_number)
        
        # Process the ticket_number to generate an object ID
        # For demonstration, we'll just return the ticket_number as the object ID
        # Replace this logic with actual conversion logic if needed
        object_id = f"obj_{ticket_number}"
    
        return object_id
    except Exception:
        LOGGER.exception(f"An error occured getting the object id for ticket '{ticket_number}'.")
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
            result = _push_to_map(ticket_dictionary)
        
        
        LOGGER.info('End run')
        