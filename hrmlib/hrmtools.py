import logging
import datetime
from azure.keyvault.secrets import SecretClient
from azure.functions import HttpRequest
from azure.identity import DefaultAzureCredential
from bs4 import BeautifulSoup
from os import getenv
from typing import List
from azure.mgmt.web import WebSiteManagementClient

# last updated 2024-02-27


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
                "KEY_VAULT_NAME was successfully identified in the environment variables.")
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
        secret_value = "?"

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
