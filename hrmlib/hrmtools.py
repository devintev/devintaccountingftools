import logging
import yaml
import os
import re
import datetime
from io import StringIO, BytesIO
import pandas as pd
from azure.keyvault.secrets import SecretClient
from azure.functions import HttpRequest
from azure.identity import DefaultAzureCredential
from bs4 import BeautifulSoup
from os import getenv
from typing import List
from azure.mgmt.web import WebSiteManagementClient
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.cosmos import CosmosClient
import azure.cosmos.exceptions as cdbexceptions

# last updated 2024-10-09
from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId)
# from openpyxl import Workbook, workbook, styles, load_workbook
# from openpyxl.worksheet.worksheet import Worksheet
# from openpyxl.utils.dataframe import dataframe_to_rows
# import pymsteams

# from tempfile import NamedTemporaryFile


class SecretsAndSettingsManager:
    """
    This class manages secrets and settings, specifically for Azure Key Vault.

    Attributes:
    logger (logging.Logger): The logger to use for logging messages.
    key_vault_client (azure.keyvault.secrets.SecretClient): The client to use for accessing the Azure Key Vault.
    """

    def __init__(self, parent_logger=None):
        """
        Initializes the SecretsAndSettingsManager.

        Parameters:
        parent_logger (logging.Logger, optional): The parent logger. If none is provided, a new logger is created.
        """

        try:
            if parent_logger is not None:
                self.logger = parent_logger.getChild(__class__.__name__)
            else:
                self.logger = logging.getLogger(
                    f"{__name__}.{__class__.__name__}")
        except:
            self.logger = logging.getLogger(__name__)
        try:
            self.credential = DefaultAzureCredential(
                exclude_developer_cli_credential=False)
            self.logger.debug(
                "Obtaining Azure Default Credentials succeeded.")
        except:
            self.logger.error("Obtaining Azure Default Credentials failed.")
            self.credential = None
        key_vault_name = getenv("KEY_VAULT_NAME", None)
        if key_vault_name:
            self.logger.debug(
                "KEY_VAULT_NAME was successfully identified in the environment variables: " + key_vault_name)
            key_vault_Uri = f"https://{key_vault_name}.vault.azure.net"
            if self.credential is not None:
                try:
                    self.key_vault_client = SecretClient(
                        vault_url=key_vault_Uri, credential=self.credential)
                    self.logger.debug(
                        "SecretClient was successfully created.")
                except:
                    self.logger.critical("Creating SecretClient failed.")
                    self.key_vault_client = None
            else:
                self.logger.critical(
                    "KEY_VAULT_NAME is was found in environment variables but credential is None.")
                self.key_vault_client = None
        else:
            self.logger.critical(
                "KEY_VAULT_NAME is not found in environment variables.")
            self.key_vault_client = None

    def get_secret(self, secret_name) -> str:
        """
        Retrieves a secret from the Azure Key Vault.

        Parameters:
        secret_name (str): The name of the secret to retrieve.

        Returns:
        str: The value of the secret. If the secret could not be retrieved, returns None.
        """
        secret_value = ""
        if self.key_vault_client is not None:
            try:
                secret = self.key_vault_client.get_secret(secret_name)
                secret_value = secret.value
            except:
                self.logger.error(
                    f"Getting secret {secret_name} from key vault failed.")
                secret = None
                try:
                    secrets = self.key_vault_client.list_properties_of_secrets()
                    secret_names = list(
                        [secret_item.name for secret_item in secrets])
                    if secret_name in secret_names:
                        self.logger.error(
                            f"Secret {secret_name} is in list of secrets but could not be retrieved. Check the keyvault's access policies in Azure Portal.")
                    else:
                        self.logger.error(
                            f"Secret {secret_name} is not in list of {len(secret_names)} secrets of the keyvault. Check the keyvault's access policies in Azure Portal.")
                except:
                    self.logger.error(
                        "Getting list of secrets failed. Check access policies of keyvault in Azure Portal.")
                    secret_names = None
        else:
            self.logger.error(
                "KEY_VAULT_NAME is not set in environment variables.")
            secret = None
        return secret_value

    def get_function_app_url(self) -> str:
        """
        Retrieves the URL of the Azure Function App.

        This method first attempts to retrieve the Function App URL from the 'AZURE_FUNCTION_APP_URL' environment variable.

        If 'AZURE_FUNCTION_APP_URL' is not set, it then checks if 'AZURE_SUBSCRIPTION_ID', 'AZURE_RESOURCE_GROUP_NAME', and 'AZURE_FUNCTION_APP_NAME' environment variables are set. If they are, it uses the Azure SDK's WebSiteManagementClient with the provided Azure credentials to fetch the Function App's details and construct the URL.

        If any of the required environment variables are not set, or if an error occurs while creating the WebSiteManagementClient, it logs an error and returns an empty string.

        Returns:
        str: The URL of the Function App. If the URL could not be retrieved, returns an empty string.
        """

        function_app_url = getenv('AZURE_FUNCTION_APP_URL')
        if function_app_url is None:
            function_app_url = ""
            self.logger.warning(
                "AZURE_FUNCTION_APP_URL is not set in environment variables. Trying to obtain function app URL from Azure SDK.")
            subscription_id = getenv("AZURE_SUBSCRIPTION_ID")
            resource_group_name = getenv("AZURE_RESOURCE_GROUP_NAME")
            function_app_name = getenv("AZURE_FUNCTION_APP_NAME")
            if subscription_id is not None and resource_group_name is not None and function_app_name is not None:
                self.logger.debug(
                    "Found AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP_NAME, and AZURE_FUNCTION_APP_NAME in environment variables.")
                if self.credential is not None:
                    self.logger.debug("Creating WebSiteManagementClient.")
                    try:
                        client = WebSiteManagementClient(
                            self.credential, subscription_id)
                        function_app = client.web_apps.get(
                            resource_group_name, function_app_name)
                        function_app_url = f"https://{function_app.default_host_name}"
                    except Exception as e:
                        self.logger.error(
                            f"Creating WebSiteManagementClient failed: {e}")
                else:
                    self.logger.error(
                        "Creating WebSiteManagementClient failed because: azure credential is missing and AZURE_FUNCTION_APP_URL is also not set in environment variables.")
            else:
                self.logger.error(
                    "Neither AZURE_FUNCTION_APP_URL nor all of AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP_NAME, AZURE_FUNCTION_APP_NAME are set in environment variables. Cannot obtain function app URL.")
        self.logger.debug(f"Obtained function app URL: '{function_app_url}'")
        return function_app_url


class HTMLListHandler(logging.Handler):
    """
    This class is a custom logging handler that stores log records in a list and can output them as an HTML table.

    Attributes:
    log_list (list): A list that stores the log records.
    """

    def __init__(self):
        super().__init__()
        self.log_list = []

    def emit(self, record):
        self.log_list.append(record)

    def get_html_log(self,
                     min_include_level=logging.DEBUG,
                     show_columns: List[str] = [
                         "Level", "Message", "Time", "Location", "Function"]
                     ) -> str:
        """
        Returns the log records as an HTML table.

        Parameters:
        min_include_level (int, optional): The minimum log level to include in the output. Default is logging.DEBUG.
        show_columns (list, optional): A list of column names to include in the output. Default is ["Level", "Message", "Time", "Location", "Function"].

        Returns:
        str: The log records formatted as an HTML table.
        """
        print(
            f"min_include_level: {min_include_level}, type: {type(min_include_level)}")
        # LogRecord-Attribute
        #
        # name: Der Name des Loggers, der den Log-Record erstellt hat.
        # msg: Die Log-Nachricht.
        # args: Die Argumente, die in die Log-Nachricht eingefügt werden.
        # levelname: Der Text, der den Schweregrad der Log-Nachricht repräsentiert, z.B. 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
        # levelno: Die numerische Darstellung des Schweregrads der Log-Nachricht.
        # pathname: Der vollständige Pfadname der Quelldatei, in der der Logger aufgerufen wurde.
        # filename: Der Dateiname der Quelldatei, in der der Logger aufgerufen wurde.
        # module: Der Modulname, in dem der Logger aufgerufen wurde.
        # lineno: Die Zeilennummer in der Quelldatei, an der der Logger aufgerufen wurde.
        # funcName: Der Name der Funktion oder Methode, in der der Logger aufgerufen wurde.
        # created: Die Zeit, zu der der Log-Record erstellt wurde (als Zeitstempel).
        # msecs: Die Millisekunden-Teil der Erstellungszeit.
        # relativeCreated: Die Zeit in Millisekunden zwischen der Erstellung des Log-Records und der Erstellung des Root-Loggers.
        # thread: Die Thread-ID.
        # threadName: Der Thread-Name.
        # process: Die Prozess-ID.
        # processName: Der Prozessname.
        # exception: Informationen über eine Ausnahme (falls vorhanden).

        table_columns = {"Level": "levelname", "Location": "name", "Line": "lineno",
                         "Function": "funcName", "Path": "pathname", "Time": "created", "Message": "msg"}
        show_columns = ["Level", "Message",
                        "Time", "Location", "Line", "Function"]

        html_log = ''
        records = [
            record for record in self.log_list if record.levelno >= min_include_level]
        print(
            f"all records: {len(self.log_list)}, filtered records: {len(records)}")
        if records:
            html_log += '<table class="logtable">\n'
            html_log += "<tr>\n"
            for col in show_columns:
                html_log += f"<th>{col}</th>\n"
            html_log += "</tr>\n"
        for record in records:
            html_log += "<tr>\n"
            for col in show_columns:
                cell_class = f"logcell_{col.lower()} logcell_{record.levelname.lower()}"
                if col == "Time":
                    value = datetime.datetime.fromtimestamp(
                        getattr(record, table_columns[col])).astimezone()
                    value = value.strftime(
                        "%H:%M:%S") + "." + str(value.microsecond // 100)[:4]
                else:
                    value = getattr(record, table_columns[col])
                html_log += f'<td class="{cell_class}">{value}</td>\n'
            html_log += "</tr>\n"
        if records:
            html_log += "</table>\n"
        return html_log


def read_html_page_template(
        filename_html,
        filename_css="assets/styles.css",
        filename_js="assets/includes.js"
) -> str:
    """
    This function reads an HTML page template and optionally a CSS file,
    and returns the HTML string with the CSS embedded.

    Parameters:
    filename_html (str): The path to the HTML file.
    filename_css (str, optional): The path to the CSS file. If none is provided,
                            no styles are embedded. Default is "assets/styles.css".

    Returns:
    str: The HTML string with the CSS embedded. If a CSS file was provided,
        its contents are embedded within a <style> tag. If no CSS file was
        provided, the HTML string is returned as is.
    """

    template_html_string = ""
    styles_string = ""
    replace_data: dict[str, str] = {}
    with open(filename_html, "r") as template_file:
        template_html_string = template_file.read()
    if filename_css is not None:
        with open(filename_css, "r") as styles_file:
            styles_string = styles_file.read()
        replace_data["styles"] = styles_string
    else:
        replace_data["styles"] = ""
    if filename_js is not None:
        with open(filename_js, "r") as js_file:
            js_string = js_file.read()
        replace_data["js_script"] = js_string
    else:
        replace_data["js_script"] = ""
    for key, value in replace_data.items():
        template_html_string = template_html_string.replace(
            "{{" + key + "}}", value)
    soup = BeautifulSoup(template_html_string, 'html.parser')
    return soup.prettify()


def extract_data_from_received_http_request(http_request: HttpRequest, parent_logger=None) -> dict:
    """
    This function extracts data from a received HTTP request.

    Parameters:
    http_request (HttpRequest): The received HTTP request.
    parent_logger (logging.Logger, optional): The parent logger. If none is provided, a new logger is created.

    Returns:
    dict: A dictionary containing the extracted data. For a POST request, the data is extracted from the request body and URL-encoded characters are replaced. For a GET request, the data is extracted from the request parameters and numbers are converted to int or float.

    Raises:
    Exception: If there is an error in decoding the request body or converting the numbers.
    """

    try:
        if parent_logger is not None:
            logger = parent_logger.getChild(__name__)
        else:
            logger = logging.getLogger(f"{__name__}")
    except:
        logger = logging.getLogger(__name__)

    def replace_post_chars(string):
        # see https://www.w3schools.com/tags/ref_urlencode.ASP
        rs = {"+": " ", "%E2%80%9C": "\"", "%2C": ",", "%3A": ":", "%2F": "/", "%3F": "?", "%3D": "=", "%26": "&", "%23": "#",
              "%25": "%", "%22": "\"", "%27": "'", }
        for key in rs:
            string = string.replace(key, rs[key])
        return string

    data = {
        "method": http_request.method,
        "url": http_request.url,
        "header": type(http_request.headers),
        "data": {}
    }
    post_data = {}
    if http_request.method == "POST":
        post_data_raw = http_request.get_body().decode("utf-8").split('&')
        if post_data_raw and post_data_raw[0]:
            logger.debug(
                f"Received data via http.{data['method']} method: {post_data_raw}")
            found_variables = set()
            for post_data_item in post_data_raw:
                [variable_name, value] = post_data_item.split('=')
                if variable_name in found_variables:
                    if type(post_data[variable_name]) is not list:
                        post_data[variable_name] = [post_data[variable_name]]
                    post_data[variable_name].append(replace_post_chars(value))
                else:
                    post_data[variable_name] = replace_post_chars(value)
                found_variables.add(variable_name)
    elif http_request.method == "GET":
        post_data = dict(http_request.params)

    # loop over all post_data items and convert numbers to int or float if they are of type string using try/except
    for key, value in post_data.items():
        if isinstance(value, str):
            try:
                post_data[key] = int(value)
            except ValueError:
                try:
                    post_data[key] = float(value)
                except ValueError:
                    pass
    return post_data


def replace_and_format_html_template(html_template, replace_data):
    """
    Replaces placeholders in an HTML template with corresponding values and formats the resulting HTML string.

    Parameters:
    html_template (str): The HTML template containing placeholders in the form "{{key}}".
    replace_data (dict): A dictionary containing key-value pairs. Each key corresponds to a placeholder in the HTML template and its value is the value to replace the placeholder with.

    Returns:
    str: The formatted HTML string where all placeholders have been replaced with their corresponding values.
    """
    for key, value in replace_data.items():
        html_template = html_template.replace("{{" + key + "}}", value)
    soup = BeautifulSoup(html_template, 'html.parser')
    html_template = soup.prettify(formatter="html5")
    return html_template
# .prettify(formatter="html5")


def get_db_config_from_keyvault(config: SecretsAndSettingsManager, logger: logging.Logger) -> dict | None:  # noqa
    db_con_data = None
    try:
        db_con_data = {
            "host": config.get_secret("wordpress-db-main-host"),
            "database": config.get_secret("wordpress-db-main-database-name"),
            "username": config.get_secret("wordpress-db-main-user"),
            "password": config.get_secret("wordpress-db-main-password")
        }
    except:
        logger.error(
            "Getting database connection data from keyvault failed.")
    return db_con_data


class DevIntConnector:

    def __init__(self, parent_logger=None, settings_file='devint_settings.yaml'):
        try:
            if parent_logger is not None:
                self.logger = parent_logger.getChild(__class__.__name__)
            else:
                self.logger = logging.getLogger(
                    f"{__name__}.{__class__.__name__}")
        except:
            self.logger = logging.getLogger(__name__)

        self.key_vault: SecretsAndSettingsManager | None = None
        self.conn_clients = None
        self.settings = self.load_settings(settings_file)

    def load_settings(self, settings_file):
        try:
            with open(settings_file, 'r') as file:
                settings = yaml.safe_load(file)
                self.logger.debug(
                    f"Successfully loaded settings from {os.path.abspath(settings_file)}.")
                return settings
        except FileNotFoundError:
            self.logger.error(
                f"Settings file '{settings_file}' not found. Python tried to find it in directory: {os.path.abspath(settings_file)}.")
        except yaml.YAMLError as e:
            self.logger.error(
                f"Error parsing YAML file '{settings_file}': {str(e)}")
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while loading settings from '{settings_file}': {str(e)}")
        return {}

    def get_settings(self):
        return self.settings

    def set_key_vault_access(self, config: SecretsAndSettingsManager):
        self.key_vault = config

    def setup(self, config: SecretsAndSettingsManager | None = None):
        if config:
            self.set_key_vault_access(config)
        if self.key_vault:
            self.conn_clients = self.build_clients()

    def build_clients(self):
        # Load settings
        settings = self.settings

        # Azure Blob Storage Information and Client
        blob_storage_account_name = settings.get(
            'azure_blob_storage_account_name')
        abs_acct_url = f"https://{blob_storage_account_name}.blob.core.windows.net/"
        try:
            blob_service_client = BlobServiceClient(
                abs_acct_url, credential=self.key_vault.credential)
            self.logger.debug(
                f"Successfully created BlobServiceClient for account: {blob_storage_account_name}.")
        except Exception as e:
            self.logger.error(
                f"Failed to create BlobServiceClient for account: {blob_storage_account_name}. Error: {str(e)}")
            return None

        # Blob Container Names
        templates_container_name = settings['blob_containers']['templates']
        financialplanning_container_name = settings['blob_containers']['financialplanning']
        financial_reports_container_name = settings['blob_containers']['financial_reports']
        working_time_reports_container_name = settings['blob_containers']['working_time_reports']
        wcc_invoicing_container_name = settings['blob_containers']['wcc_invoicing']
        od_invoicing_container_name = settings['blob_containers']['od_invoicing']

        # Buchhaltungsbuttler API Information
        try:
            bb_api_key = self.key_vault.get_secret(
                settings['secrets']['bb_api_key'])
            self.logger.debug(
                "Successfully retrieved Buchhaltungsbuttler API key.")
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve Buchhaltungsbuttler API key. Error: {str(e)}")
            return None
        bb_authorization = self.key_vault.get_secret(
            settings['secrets']['bb_authorization'])
        bb_cookie = self.key_vault.get_secret(settings['secrets']['bb_cookie'])

        # Sendgrid API Information
        sendgrid_api_key = self.key_vault.get_secret(
            settings['secrets']['sendgrid_api_key'])
        try:
            sendgrid_client = SendGridAPIClient(sendgrid_api_key)
            self.logger.debug("Successfully created SendGridAPIClient.")
        except Exception as e:
            self.logger.error(
                f"Failed to create SendGridAPIClient. Error: {str(e)}")
            return None

        # Azure Cosmos DB Information and Client
        cosmos_db_url = settings.get('cosmos_db_url')
        db_access_key = self.key_vault.get_secret(
            settings['secrets']['cosmos_db_key'])
        try:
            cosmos_client = CosmosClient(
                url=cosmos_db_url, credential=db_access_key)
            self.logger.debug(
                f"Successfully created CosmosClient for URL: {cosmos_db_url}.")
        except Exception as e:
            self.logger.error(
                f"Failed to create CosmosClient for URL: {cosmos_db_url}. Error: {str(e)}")
            return None
        db_id = settings.get('cosmos_db_id')

        try:
            try:
                db = cosmos_client.create_database(id=db_id)
                self.logger.debug(
                    f"Successfully created database with id: {db_id}.")
            except cdbexceptions.CosmosResourceExistsError:
                db = cosmos_client.get_database_client(db_id)
                self.logger.debug(
                    f"Database with id: {db_id} already exists. Using existing database client.")
            except Exception as e:
                self.logger.error(
                    f"Failed to create or get Cosmos DB database with id: {db_id}. Error: {str(e)}")
                return None
        except cdbexceptions.CosmosResourceExistsError:
            db = cosmos_client.get_database_client(db_id)

        # Teams Webhook and Report Request Backlink
        try:
            teams_webhook = self.key_vault.get_secret(
                settings['secrets']['teams_webhook'])
            self.logger.debug("Successfully retrieved Teams webhook URL.")
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve Teams webhook URL. Error: {str(e)}")
            return None
        try:
            reportrequest_backlink = self.key_vault.get_secret(
                settings['secrets']['reportrequest_backlink'])
            self.logger.debug(
                "Successfully retrieved report request backlink.")
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve report request backlink. Error: {str(e)}")
            return None

        # Clients Dictionary
        self.conn_clients = {
            "blob_service": blob_service_client,
            "templates_folder": blob_service_client.get_container_client(container=templates_container_name),
            "financialplanning_folder": blob_service_client.get_container_client(container=financialplanning_container_name),
            "financial_reports_folder": blob_service_client.get_container_client(container=financial_reports_container_name),
            "working_time_reports_folder": blob_service_client.get_container_client(container=working_time_reports_container_name),
            "wcc_invoicing_folder": blob_service_client.get_container_client(container=wcc_invoicing_container_name),
            "od_invoicing_folder": blob_service_client.get_container_client(container=od_invoicing_container_name),
            "key_vault": self.key_vault,
            "cosmos": cosmos_client,
            "sendgrid": sendgrid_client,
            "teams_webhook": teams_webhook,
            "reportrequest_backlink": reportrequest_backlink,
            "bb_api_key": bb_api_key,
            "bb_authorization": bb_authorization,
            "bb_cookie": bb_cookie,
            "db": db
        }
        return self.conn_clients

    def analyse_received_http_request(self, http_request):

        def replace_post_chars(string):
            # see https://www.w3schools.com/tags/ref_urlencode.ASP
            rs = {"+": " ", "%E2%80%9C": "\"", "%2C": ",", "%3A": ":", "%2F": "/", "%3F": "?", "%3D": "=", "%26": "&", "%23": "#",
                  "%25": "%", "%22": "\"", "%27": "'", }
            for key in rs:
                string = string.replace(key, rs[key])
            return string

        data = {"method": http_request.method,
                "url": http_request.url,
                "header": type(http_request.headers),
                "data": {}
                }
        post_data = {}
        if http_request.method == "POST":
            post_data_raw = http_request.get_body().decode("utf-8").split('&')
            # case_tag_options = []
            if post_data_raw and post_data_raw[0]:
                for post_data_item in post_data_raw:
                    post_data_item_parts = post_data_item.split('=')
                    post_data[post_data_item_parts[0]] = replace_post_chars(
                        post_data_item_parts[1])
        elif http_request.method == "GET":
            post_data = dict(http_request.params)
        self.logger.log(f"received data with method: {data['method']}<br>")
        return post_data

    def download_all_sheets(self, blob_client):
        self.logger.debug(
            f"Starting download_all_sheets from {blob_client.container_name}/{blob_client.blob_name}.")

        try:
            # Initiate download stream
            self.logger.debug("Initializing blob download stream...")
            stream = BytesIO()
            blob_downloader = blob_client.download_blob()

            # Download blob data to stream
            blob_downloader.download_to_stream(stream)
            self.logger.debug(
                "Blob downloaded successfully into memory stream.")

            # Load Excel data from stream
            get_blob_data = pd.ExcelFile(stream, engine='openpyxl')
            self.logger.debug(
                f"Excel file loaded. Sheets found: {get_blob_data.sheet_names}")

            # Process each sheet and store in dictionary
            dataframes = {}
            for sheet in get_blob_data.sheet_names:
                # self.logger.debug(f"start processing sheet: {sheet}")
                new_df = pd.read_excel(
                    get_blob_data, engine='openpyxl', sheet_name=sheet)
                dataframes[sheet] = new_df
                # self.logger.debug(
                #     f"Sheet '{sheet}' read into DataFrame with {new_df.shape[0]} rows and {new_df.shape[1]} columns.")

            # self.logger.info(
            #     "All sheets downloaded and processed successfully.")
            return dataframes

        except Exception as e:
            self.logger.error(f"Error in download_all_sheets: {e}")
            raise

    def read_time_slots(self, df: pd.DataFrame):
        self.logger.debug("Starting read_time_slots function.")

        try:
            # Drop empty rows and log the result
            time_slots_df = df.dropna(how='all')
            self.logger.debug(
                f"Dropped empty rows. Remaining rows: {len(time_slots_df)}")

            # Rename columns and log the new column names
            rename_list = {'Slot Start': 'start', 'Slot End': 'end',
                           'Slot Title': 'name', 'Slot ID': 'id'}
            time_slots_df = time_slots_df.rename(
                columns=rename_list, inplace=False)
            self.logger.debug(f"Columns renamed: {rename_list}")

            # Initialize dictionary to store results
            dict_list = {}
            self.logger.debug(
                "Processing each row to extract time slot information.")

            for time_slot_ID in time_slots_df.index:
                mdict = time_slots_df.loc[time_slot_ID].to_dict()
                # self.logger.debug(f"Processing time slot ID: {time_slot_ID}")

                # Convert start and end to strings and store
                if pd.notnull(mdict.get('start')) and pd.notnull(mdict.get('end')):
                    mdict['startString'] = mdict['start'].strftime('%d.%m.%Y')
                    mdict['endString'] = mdict['end'].strftime('%d.%m.%Y')
                else:
                    self.logger.warning(
                        f"Missing start or end date for time slot ID {time_slot_ID}. Skipping conversion.")

                # Store time slot information in dictionary
                dict_list[str(mdict['id'])] = mdict

            self.logger.info("All time slots processed successfully.")
            return dict_list

        except Exception as e:
            self.logger.error(f"Error in read_time_slots: {e}")
            raise

    def read_kontenrahmen(self, dfs: dict):
        self.logger.debug("Starting read_kontenrahmen function.")

        try:
            # Initialize kontenrahmen dictionary to store processed data
            kontenrahmen = {}
            self.logger.debug(
                f"Processing {len(dfs)} dataframes for 'kontenrahmen'.")

            for key, df in dfs.items():
                self.logger.debug(f"Processing dataframe with key: {key}")
                entries = []

                for index in df.index:
                    mdict = df.loc[index].to_dict()

                    # Construct entry dictionary with required fields
                    entry = {
                        'accountRangeStart': mdict.get('Start'),
                        'accountRangeEnd': mdict.get('Ende'),
                        'type1': mdict.get('Typ 1'),
                        'type2': mdict.get('Typ 2')
                    }

                    # Check and add optional categories if they are present
                    if not pd.isna(mdict.get('Kategorie 1')):
                        entry['category1'] = mdict['Kategorie 1']
                    if not pd.isna(mdict.get('Kategorie 2')):
                        entry['category2'] = mdict['Kategorie 2']
                    if not pd.isna(mdict.get('Kategorie 3')):
                        entry['category3'] = mdict['Kategorie 3']
                    entries.append(entry)

                # Store entries list in kontenrahmen dictionary with a modified key name
                kontenrahmen[key[13:]] = entries
                self.logger.debug(
                    f"Processed {len(entries)} entries for key '{key[13:]}'.")

            # Set a default kontenrahmen entry
            kontenrahmen['default'] = kontenrahmen[list(
                kontenrahmen.keys())[0]]
            self.logger.debug(
                "Default kontenrahmen set to the first processed entry.")

            self.logger.info(
                "Completed processing all dataframes for 'kontenrahmen'.")
            return kontenrahmen

        except Exception as e:
            self.logger.error(f"Error in read_kontenrahmen: {e}")
            raise

    def read_kostenstellenplan(self, df: pd.DataFrame):
        self.logger.debug("Starting read_kostenstellenplan function.")

        try:
            # Initialize costlocations dictionary to store processed data
            costlocations = {}

            # Drop empty rows and rename relevant columns
            ksp_df = df.dropna(how='all')
            self.logger.info(
                f"Dropped empty rows. Remaining rows: {len(ksp_df)}")
            ksp_df = ksp_df.rename(
                columns={
                    'Unnamed: 5': 'sectionname', 'Unnamed: 6': 'groupName',
                    'Unnamed: 7': 'subGroupName', 'Unnamed: 8': 'name', 'Unnamed: 9': 'type'
                },
                inplace=False
            )
            # self.logger.debug("Renamed columns as per mapping.")

            # Drop rows missing key identifier
            ksp_df = ksp_df.dropna(subset=['Unnamed: 1'])
            max_costlocation_digits = 4
            self.logger.info("Starting to process each row in the dataframe.")

            for ksp_df_index in ksp_df.index:
                item = {"limits": {}}
                mdict = ksp_df.loc[ksp_df_index].to_dict()
                # self.logger.debug(f"Processing row at index {ksp_df_index}")

                # Determine item type based on type column
                if not pd.isna(mdict['type']):
                    if mdict['type'] in ['income', 'Einnahmen']:
                        item['type'] = 'income'
                    elif mdict['type'] in ['expense', 'Ausgaben']:
                        item['type'] = 'expense'
                    elif mdict['type'] == 'budget':
                        item['type'] = 'budget'
                    # self.logger.debug(f"Set item type for index {ksp_df_index}: {item['type']}")

                # Process limits
                if not pd.isna(mdict.get('Unnamed: 10')):
                    item['limits']['max'] = float(mdict['Unnamed: 10'])
                    # self.logger.debug(f"Set max limit for index {ksp_df_index}: {item['limits']['max']}")
                if not pd.isna(mdict.get('Unnamed: 11')):
                    item['limits']['extendedMax'] = float(mdict['Unnamed: 11'])
                    # self.logger.debug(f"Set extended max limit for index {ksp_df_index}: {item['limits']['extendedMax']}")

                # Handle group items
                if not pd.isna(mdict.get('groupName')) or not pd.isna(mdict.get('subGroupName')):
                    item['type'] = 'group'
                    item['name'] = mdict['subGroupName'] if not pd.isna(
                        mdict.get('subGroupName')) else mdict['groupName']
                    # self.logger.debug(f"Set item as group with name '{item['name']}'")

                    # Construct the ID and range of the cost location
                    starting_digits = "".join(str(int(mdict[col])) for col in [
                                              'Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3'] if not pd.isna(mdict[col]))
                    min_digits = starting_digits + '0' * \
                        (max_costlocation_digits - len(starting_digits))
                    max_digits = starting_digits + '9' * \
                        (max_costlocation_digits - len(starting_digits))

                    item.update({
                        'id': starting_digits,
                        'costLocations': {
                            'startingDigits': starting_digits,
                            'min': int(min_digits),
                            'max': int(max_digits)
                        },
                        'children': {}
                    })
                    costlocations[item['id']] = item
                    # self.logger.debug(f"Group item with ID '{item['id']}' has range {min_digits} - {max_digits}")

                # Handle individual items
                elif not pd.isna(mdict.get('name')):
                    item['type'] = 'item'
                    item['name'] = mdict['name']
                    digits = "".join(str(int(mdict[col])) for col in [
                                     'Unnamed: 0', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3'] if not pd.isna(mdict[col]))
                    item['number'] = int(digits)
                    item['id'] = digits
                    costlocations[item['id']] = item
                    # self.logger.debug(f"Item with ID '{item['id']}' and name '{item['name']}' added.")

            # Assign children to groups based on their ranges
            self.logger.debug(
                "Assigning children to groups based on cost location ranges.")
            for id, item in costlocations.items():
                if item['type'] == 'group':
                    for child_id, child_item in costlocations.items():
                        if child_item['type'] == 'item' and item['costLocations']['min'] <= child_item['number'] <= item['costLocations']['max']:
                            item['children'][child_id] = child_item
                            # self.logger.debug(f"Added item '{child_id}' as a child of group '{id}'")
                        elif child_item['type'] == 'group' and child_id != id and item['costLocations']['min'] <= child_item['costLocations']['min'] and item['costLocations']['max'] >= child_item['costLocations']['max']:
                            item['children'][child_id] = child_item
                            # self.logger.debug(f"Added group '{child_id}' as a subgroup of '{id}'")

            self.logger.info("Completed processing kostenstellenplan.")
            return costlocations

        except Exception as e:
            self.logger.error(f"Error in read_kostenstellenplan: {e}")
            raise

    def read_reports_overview(self, df: pd.DataFrame):
        self.logger.debug("Starting read_reports_overview function.")

        # Initialize dictionary to store reports and counter for ignored reports
        reports = {}
        ignored_reports = 0
        self.logger.debug("Processing report entries in the dataframe.")

        for report_ID in df.index:
            mdict = df.loc[report_ID].to_dict()
            report = {
                'id': mdict["Plan"],
                'name': mdict['Name'],
                'costLocationsRange': {
                    'min': mdict['Kostenstellenstart'],
                    'max': mdict['Kostenstellenende']
                }
            }

            # Include only reports with version 2
            if mdict['Version'] == 2:
                reports[mdict["Plan"]] = report
                self.logger.debug(
                    f"Added report with ID '{report['id']}' and name '{report['name']}'.")
            else:
                ignored_reports += 1
                self.logger.debug(
                    f"Ignored report with ID '{report['id']}' due to deprecated version.")

        # Log ignored reports if any
        if ignored_reports > 0:
            self.logger.warning(
                f"{ignored_reports} report plans were not read because of their deprecated version.")

        self.logger.debug("Completed processing all report entries.")
        return reports

    def read_report_schema_into(self, report: dict, schema_df: pd.DataFrame, time_slot_templates: dict):
        self.logger.debug("Starting read_report_schema_into function.")

        try:
            # Clean the DataFrame by dropping empty rows and columns
            schema_df.dropna(how='all', inplace=True)
            schema_df.dropna(axis=1, how="all", inplace=True)
            self.logger.debug(
                "Dropped empty rows and columns from schema DataFrame.")

            # Identify slot columns and section columns
            slot_columns = [
                col for col in schema_df.columns if col.startswith('s:')]
            slot_names = [col.split(':')[1] for col in slot_columns]
            section_column_names = [
                col for col in schema_df.columns if col.startswith('Section ')]
            self.logger.debug(
                f"Found {len(slot_columns)} slot columns and {len(section_column_names)} section columns.")

            # Process slot data
            slots_data = []
            listings_data = []
            order_number = 0
            for slot_column in slot_columns:
                slot_data = {
                    'timeSlotId': slot_column.split(':')[1],
                    'buildListing': len(slot_column.split(':')) > 2 and slot_column.split(':')[2] == "listing",
                    'orderNumber': order_number
                }
                order_number += 1

                # Adjust slot ID if necessary and retrieve slot info
                if re.findall(r'\.\d$', slot_data['timeSlotId']) and slot_data['timeSlotId'][:-2] in slot_names:
                    slot_data['timeSlotId'] = slot_data['timeSlotId'][:-2]
                slot_template = time_slot_templates.get(
                    slot_data['timeSlotId'], {})
                slot_data.update({
                    'name': slot_template.get('name'),
                    'start': slot_template.get('start'),
                    'end': slot_template.get('end')
                })
                slots_data.append(slot_data)
                if slot_data['buildListing']:
                    listings_data.append(slot_data)
                # self.logger.debug(f"Processed slot column '{slot_column}' with order number {slot_data['orderNumber']}.")

            report['slots'] = slots_data
            report['numberSectionLevels'] = len(section_column_names)

            # Process items in schema
            items = []
            order_number = 0
            for row_id in schema_df.index:
                mdict = schema_df.loc[row_id].to_dict()
                item = {'orderNumber': order_number}
                order_number += 1
                hierarchy_location = [
                    mdict[col] for col in section_column_names if not pd.isna(mdict[col])
                ]
                item['hierarchyLocation'] = hierarchy_location

                # Populate item details based on type
                item['name'] = mdict.get('Name', '') if not pd.isna(
                    mdict.get('Name')) else ''
                item['type'] = mdict['Type'].lower() if mdict['Type'].lower() in [
                    'income', 'expense', 'group'] else 'unknown'

                if item['type'] in ['expense', 'income']:
                    cost_loc_str = mdict['Cost Location'] if isinstance(
                        mdict['Cost Location'], str) else f"{int(mdict['Cost Location']):04d}"
                    item['costLocationsStrings'] = cost_loc_str.split(',')
                    item['costLocations'] = [
                        int(cl) for cl in item['costLocationsStrings']]
                    item['hierarchyLocation'].append(item['name'])
                elif item['type'] == 'group' and hierarchy_location:
                    item['name'] = hierarchy_location[-1]

                # Process slot-specific info
                slots_info = []
                for report_slot in report['slots']:
                    row_slot_info = {
                        'timeSlotId': report_slot['timeSlotId'],
                        'buildListing': report_slot['buildListing'],
                        'slotDetails': report_slot,
                        'orderNumber': report_slot['orderNumber']
                    }
                    column_name = f"s:{report_slot['timeSlotId']}"
                    if row_slot_info['buildListing']:
                        column_name += ":listing"

                    # Parse values and set type/limits
                    value = mdict.get(column_name)
                    if not pd.isna(value):
                        if isinstance(value, str):
                            row_slot_info['type'] = 'sum' if value.lower() in ['fieldsum', 'cellsum', 'sum', 'summe'] else 'bookings' if value.lower() in [
                                'bookings', 'buchungen'] else 'budget'
                            if ':' in value:
                                limit, *extra = value.split(':')
                                row_slot_info['limit'] = float(limit)
                                row_slot_info['limitType'] = 'absolute' if extra and extra[0] == '!' else 'exceedable' if extra and extra[0].startswith(
                                    '+') else 'relative'
                                if extra and extra[0].startswith('+') and extra[0].endswith('%'):
                                    row_slot_info['extendedLimit'] = row_slot_info['limit'] * (
                                        1.0 + float(extra[0][1:-1]) / 100.0)
                        elif isinstance(value, (int, float)):
                            row_slot_info.update(
                                {'type': 'budget', 'limit': float(value), 'limitType': 'relative'})
                    else:
                        row_slot_info.update(
                            {'type': 'empty', 'limit': 0.0, 'limitType': 'relative'})

                    slots_info.append(row_slot_info)
                    # self.logger.debug(f"Processed slot info for item {item['name']} with slot ID '{report_slot['timeSlotId']}'.")

                item['slots'] = slots_info
                items.append(item)

            # Collect cost locations and strings
            report['costLocations'] = list({loc for i in items if i['type'] in [
                                           'expense', 'income'] for loc in i['costLocations']})
            report['costLocationsStrings'] = list({str for i in items if i['type'] in [
                                                  'expense', 'income'] for str in i['costLocationsStrings']})

            # Assign children to groups
            for row in items:
                if row['type'] == 'group':
                    row['children'] = [
                        item for item in items
                        if len(item['hierarchyLocation']) == len(row['hierarchyLocation']) + 1
                        and item['hierarchyLocation'][:-1] == row['hierarchyLocation']
                    ]
                    # if row['children']:
                    #     self.logger.debug(f"Assigned {len(row['children'])} children to group '{row['name']}'.")

            report['rows'] = items
            if listings_data:
                report['listings'] = listings_data
            self.logger.debug("Completed processing report schema.")

        except Exception as e:
            self.logger.error(f"Error in read_report_schema_into: {e}")
            raise

    def read_distribution_instructions(self, df: pd.DataFrame):
        self.logger.debug("Starting read_distribution_instructions function.")

        try:
            # Initialize distribution list
            dist = []
            self.logger.debug("Processing each row in the dataframe.")

            for row_id in df.index:
                mdict = df.loc[row_id].to_dict()
                entry = {'channelType': mdict['type'], 'packages': []}
                # self.logger.debug(
                #     f"Processing distribution entry with channel type '{mdict['type']}'.")

                # Check and add recipient if available
                if not pd.isna(mdict.get('recipient')):
                    entry['recipient'] = mdict['recipient']
                    # self.logger.debug(f"Added recipient: {entry['recipient']}")

                # Process trigger information if available
                if not pd.isna(mdict.get('trigger')):
                    trigger_parts = mdict['trigger'].split(':')
                    entry['trigger'] = {'type': trigger_parts[0].strip()}
                    if len(trigger_parts) > 1:
                        entry['trigger']['condition'] = trigger_parts[1].strip()
                    # self.logger.debug(f"Added trigger: {entry['trigger']}")

                # Process content information
                if not pd.isna(mdict.get('content')):
                    content = mdict['content'].split('),')
                    # self.logger.debug(
                    #     f"Processing content for entry with {len(content)} content items.")

                    for item in content:
                        # Parse job type and job list
                        subitems = item.split('(')
                        job_type = subitems[0].strip().lower()
                        job_list_raw = subitems[1].rstrip(')') if len(
                            subitems) > 1 else ""
                        content_items = []

                        # Parse individual jobs within the job list
                        for job in job_list_raw.split(','):
                            job_parts = job.split(':')
                            if len(job_parts) == 2:
                                citem = {'type': job_parts[0].strip(
                                ), 'scope': job_parts[1].strip()}
                                content_items.append(citem)
                                # self.logger.debug(
                                #     f"Added content item: {citem}")
                            else:
                                self.logger.warning(
                                    f"Invalid job format in content item: '{job}'")

                        # Append processed package to entry packages
                        entry['packages'].append(
                            {'packageType': job_type, 'content': content_items})
                        self.logger.debug(
                            f"Added package '{job_type}' with {len(content_items)} content items to entry.")

                # Append completed entry to the distribution list
                dist.append(entry)
                self.logger.debug(
                    f"Completed processing entry with channel type '{mdict['type']}'.")

            self.logger.debug(
                "Completed processing all distribution instructions.")
            return dist

        except Exception as e:
            self.logger.error(f"Error in read_distribution_instructions: {e}")
            raise

    def read_instruction_files(self, container=None):
        self.logger.debug("Starting read_instruction_files function.")

        # Determine container
        container = container or self.conn_clients["templates_folder"]
        self.logger.debug(f"Using container: {container.container_name}")

        # Initialize instructions structure
        instructions = {
            "sheets": {},
            "unprocessedSheets": {},
            "processedSheets": {}
        }

        # List and process blobs in container
        self.logger.debug("Listing blobs in container...")
        instruction_files_list = container.list_blobs()
        file_count = 0

        for instruction_file in instruction_files_list:
            file_count += 1
            blob_client = container.get_blob_client(instruction_file.name)
            self.logger.debug(f"Processing file {instruction_file.name}")

            # Process only .xlsx files
            if instruction_file.name.endswith(".xlsx"):
                self.logger.debug(
                    f"Identified Excel file: {instruction_file.name}")
                dataframes = self.download_all_sheets(blob_client)
                for key, df in dataframes.items():
                    instructions["sheets"][key] = df
                    instructions["unprocessedSheets"][key] = df

        if file_count == 0:
            self.logger.warning("No files found in the container.")
        else:
            self.logger.info(
                f"Total instruction files processed: {file_count}")

        # Time Slots
        if "Time Slots" in instructions["unprocessedSheets"]:
            self.logger.debug("Found 'Time Slots' sheet.")
            instructions["timeSlotTemplates"] = self.read_time_slots(
                instructions["unprocessedSheets"]["Time Slots"]
            )
            instructions["processedSheets"]["Time Slots"] = instructions["unprocessedSheets"]["Time Slots"]
            del instructions["unprocessedSheets"]["Time Slots"]
        else:
            self.logger.error("No 'Time Slots' sheet found in any Excel file.")

        # Kontenrahmen
        kontenrahmen = {k: v for k, v in instructions["unprocessedSheets"].items(
        ) if k.startswith('Kontenrahmen ')}
        if kontenrahmen:
            self.logger.info(
                f"Found {len(kontenrahmen)} 'Kontenrahmen' sheets.")
            instructions["kontenrahmen"] = self.read_kontenrahmen(kontenrahmen)
            instructions["processedSheets"].update(kontenrahmen)
            for key in kontenrahmen:
                del instructions["unprocessedSheets"][key]
        else:
            self.logger.error(
                "No 'Kontenrahmen' sheet found in any Excel file.")

        # Kostenstellenplan
        if "Kostenstellenplan" in instructions["unprocessedSheets"]:
            self.logger.info("Found 'Kostenstellenplan' sheet.")
            instructions["kostenstellenplan"] = self.read_kostenstellenplan(
                instructions["unprocessedSheets"]["Kostenstellenplan"]
            )
            instructions["processedSheets"]["Kostenstellenplan"] = instructions["unprocessedSheets"]["Kostenstellenplan"]
            del instructions["unprocessedSheets"]["Kostenstellenplan"]
        else:
            self.logger.error(
                "No 'Kostenstellenplan' sheet found in any Excel file.")

        # Reports Overview
        if "Reports Overview" in instructions["unprocessedSheets"]:
            self.logger.info("Found 'Reports Overview' sheet.")
            # Uncomment below if reports overview processing is needed
            instructions["reports"] = self.read_reports_overview(
                instructions["unprocessedSheets"]["Reports Overview"]
            )
            instructions["processedSheets"]["Reports Overview"] = instructions["unprocessedSheets"]["Reports Overview"]
            del instructions["unprocessedSheets"]["Reports Overview"]
        else:
            self.logger.error(
                "No 'Reports Overview' sheet found in any Excel file.")

        # Budget Plans
        if "reports" in instructions:
            self.logger.info("Processing reports for budget plans.")
            for key, report in instructions['reports'].items():
                sheet_name = f"Budget Plan {key}"
                if sheet_name in instructions["unprocessedSheets"]:
                    self.read_report_schema_into(
                        report, instructions["unprocessedSheets"][sheet_name], instructions["timeSlotTemplates"]
                    )
                    instructions["processedSheets"][sheet_name] = instructions["unprocessedSheets"][sheet_name]
                    del instructions["unprocessedSheets"][sheet_name]
                else:
                    self.logger.warning(
                        f"Budget Plan {key} not found in unprocessed sheets.")
        else:
            self.logger.error(
                "No 'reports' key found in instructions dictionary.")

        # Flow Plan
        if "Flow Plan" in instructions["unprocessedSheets"]:
            self.logger.info("Found 'Flow Plan' sheet.")
            instructions["distribution"] = self.read_distribution_instructions(
                instructions["unprocessedSheets"]["Flow Plan"]
            )
            instructions["processedSheets"]["Flow Plan"] = instructions["unprocessedSheets"]["Flow Plan"]
            del instructions["unprocessedSheets"]["Flow Plan"]
        else:
            self.logger.error("No 'Flow Plan' sheet found in any Excel file.")

        self.logger.info("Completed reading instruction files.")
        return instructions
