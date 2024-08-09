import pylogfig
from noplaintext.crypto_utils import decrypt
import arcgis


def _website_navigation():
    pass

def _content_parsing():
    pass



class OcGisApp:
    def __init__(self, config: pylogfig.Config):
        self.config = config
    
    def _setup(self):
        arcgis_username = self.config.get('arcgis.username')
        arcgis_password = self.config.get('arcgis.password')
        key_file = self.config.get('key_path')
        self.gis = arcgis.GIS(self.config.get('arcgis.url'), decrypt(arcgis_username, key_file), decrypt(arcgis_password, key_file))
        self.layer = arcgis.features.FeatureLayer(self.config.get('arcgis.layer_url'))
        
    def run(self):
        pass