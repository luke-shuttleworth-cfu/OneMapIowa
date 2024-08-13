# OcGisApp

## Overview

`OcGisApp` is a Python application designed to interact with ArcGIS Online and the Iowa One Call website to manage and update feature layers. The application uses Selenium for web scraping, ArcGIS API for feature layer management, and provides functionality for processing and updating tickets based on their status.

## Installation

1. **Dependencies**: Ensure you have the required Python packages installed. You can install them using pip:

    ```bash
    pip install arcgis lxml beautifulsoup4 selenium
    ```

2. **WebDriver**: Download the Microsoft Edge WebDriver from [Microsoft Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/) and ensure it's available in your system's PATH.

1. **App**: Install the package for the app:

    ```bash
    pip install ocgis
    ```

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
    state='your_state',
    headless=True
)
```

### Running the Application

To execute the main functionality of the application, call the `run` method:

```python
app.run()
```

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

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
