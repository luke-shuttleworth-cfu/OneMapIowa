# OcGisApp

## Overview

`OcGisApp` is a Python application designed to interact with ArcGIS Online and the Iowa One Call website to manage and update feature layers. The application uses Selenium for web scraping, ArcGIS API for feature layer management, and provides functionality for processing and updating tickets based on their status.

## Installation

1. **Dependencies**: Ensure you have the required Python packages installed. You can install them using pip:

    ```bash
    pip install arcgis lxml beautifulsoup4 selenium
    ```

2. **WebDriver**: Download the Microsoft Edge WebDriver from [Microsoft Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/) and ensure it's available in your system's PATH.

3. **App**: Install the package for the app:

    ```bash
    pip install ocgis-cfu
    ```

4. **ArcGIS Online Map**: Create an ArcGIS Online map with the fields and types outlined below, in addition to your district statuses.
- originalCallDate, ```Date```
- ticketNumber, ```String```
- callType, ```String```
- expirationDate,```Date```
- callerName, ```String```
- callerPhone, ```String```
- excavatorName, ```String```
- excavatorPhone, ```String```
- excavatorAddress, ```String```
- excavatorEmail, ```String```
- onsiteContact, ```String```
- onsitePhone, ```String```
- beginWorkDate, ```Date```
- workDuration, ```String```
- workType, ```String```
- workDoneFor, ```String```
- trenching, ```String```
- boring, ```String```
- plowing, ```String```
- backhoe, ```String```
- blasting, ```String```
- other, ```String```
- markedWhite, ```String```
- digCounty, ```String```
- digCity, ```String```
- digAddres, ```String```
- digAddressAt, ```String```
- extentOfWork, ```String```
- remarks, ```String```
- deadline, ```Date```
- status, ```String```
- lastAutomaticUpdate, ```Date```
- yourdistrict1, ```String```
- yourdistrict2, ```String```

## Usage

### Initialization

Create an instance of the `OcGisApp` class with the necessary parameters:

```python
app = OcGisApp(
    arcgis_username='your_arcgis_username',
    arcgis_password='your_arcgis_password',
    arcgis_link='your_arcgis_link',
    layer_url='your_layer_url',
    onecall_username='your_onecall_username',
    onecall_password='your_onecall_password',
    onecall_login_url='your_onecall_login_url',
    districts=['district1', 'district2'],
    driver_executable_path='path_to_your_webdriver',
    update_range=30,
    state='your_state', # e.g. IA
    headless=True
)
```

### Running the Application

To execute the main functionality of the application, call the `run` method:

```python
app.run()
```

This will pull open tickets from the locator page and add them to the ArcGIS map once. Use a loop or task scheduler to run the app on an interval.

## Configuration

- **arcgis_username**: Your ArcGIS username.
- **arcgis_password**: Your ArcGIS password.
- **arcgis_link**: URL for the ArcGIS instance.
- **layer_url**: URL of the feature layer to update.
- **onecall_username**: Username for Iowa One Call.
- **onecall_password**: Password for Iowa One Call.
- **onecall_login_url**: Login URL for Iowa One Call.
- **districts**: List of district names to monitor.
- **driver_executable_path**: Path to the Edge WebDriver executable.
- **update_range**: Range of days to look back for updates.
- **state**: State to filter tickets.
- **headless**: Whether to run the browser in headless mode.
- **closed_statuses**: List of statuses indicating a closed ticket.

## Logging

The application uses the `logging` module for logging messages. Configure the logging settings as needed for your environment.

## Example Configuration File (TOML)

```toml
[arcgis]
username = "username"
password = "password"
link = "https://www.arcgis.com"
layer_url = "https://services5.arcgis.com/g3r4E4Xlpygk5wEz/arcgis/rest/services/Locate_Tickets/FeatureServer/0"

[onecall]
username = "username"
password = "password"
login_url = "https://ia.itic.occinc.com/?isite=y&db=ia&disttrans=n&basetrans=n&trans_id=0&district_code=0&record_id=0&trans_state="
closed_statuses = ["Clear", "Marked"]
districts = ["cf1", "cf2", "cf3", "cf8"]
state = "IA"

[webdriver]
headless = false
driver_executable_path = "src\\ocgis\\msedgedriver.exe"

[settings]
update_range = 50




[logging]
version = 1
disable_existing_loggers = false

[logging.formatters.detailed]
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[logging.formatters.simple]
format = "%(name)s - %(levelname)s - %(message)s"

[logging.handlers.console]
class = "logging.StreamHandler"
level = "DEBUG"
formatter = "simple"
stream = "ext://sys.stdout"

[logging.handlers.rotating_file]
class = "logging.handlers.RotatingFileHandler"
level = "INFO"
formatter = "detailed"
filename = "tests\\logs\\app.log"
maxBytes = 10485760
backupCount = 5
encoding = "utf8"

[logging.loggers."src.ocgis.ocgisapp"]
level = "DEBUG"
handlers = ["console", "rotating_file"]
propagate = false

[logging.root]
level = "WARNING"
handlers = ["console", "rotating_file"]
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
