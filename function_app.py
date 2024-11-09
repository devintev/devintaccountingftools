import azure.functions as func
import logging
from json2html import json2html
# import traceback
import sys
import os
# import json
from datetime import datetime

from libraries import common, DLogger

from hrmlib.hrmtools import (
    SecretsAndSettingsManager, HTMLListHandler,
    read_html_page_template,
    extract_data_from_received_http_request,
    replace_and_format_html_template
)
# az login --service-principal -u "03d6bd37-4f1d-4c3f-8e42-fbb00a18613c" -p "25c673f4-42a5-43c5-9d6f-f84222b09f19" --tenant "052225af-3db0-4ee8-88d8-27c19a3afed1"


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="test")
def test(req: func.HttpRequest) -> func.HttpResponse:
    # # # # # # # # # # # # # # # # # # # # # # # # # # #
    #
    #   Setting up logging and configuration and data access
    #
    # # # # # # # # # # # # # # # # # # # # # # # # # # #

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    html_log_handler = HTMLListHandler()
    html_log_handler.setLevel(logging.DEBUG)
    logger.addHandler(html_log_handler)

    print_log_handler = logging.StreamHandler()  # StreamHandler prints to console
    print_log_handler.setLevel(logging.ERROR)
    logger.addHandler(print_log_handler)

    logger.debug(
        f'Python HTTP trigger received a request and started running with python version: {str(sys.version)}.')

    logger.info(
        'Python HTTP triggered ????? function starts processing a request.')

    # dc = common.DevIntConnector()
    # dc.setup()
    # data = dc.analyse_received_http_request(req)

    # http_vars = extract_data_from_received_http_request(
    #     http_request=req, parent_logger=logger)
    # logger.debug(f"http_vars: {json2html.convert(json = http_vars)}")
    http_vars = extract_data_from_received_http_request(
        http_request=req, parent_logger=logger)
    replace_data = {
        "help_info": "",
        "reportbuilder_form": "",
        "messages": "",
        "main_content": f"<h1>Called Function</h1>",
        "report_content": "",
        "db_statistics_html": "",
        "log_level_num": "info",
    }

    config = SecretsAndSettingsManager(parent_logger=logger)
    se = config.get_secret("bb-api-key")
    logger.debug(f"Secret: {se[:4]}")

    # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    #
    #   End of function, Information output is prepared, logs and help infos added
    #
    # # # # # # # # # # # # # # # # # # # # # # # # # # #

    log_data = html_log_handler.get_html_log(
        min_include_level=logging.DEBUG)
    replace_data["log"] = "<h2>Logs</h2>" + log_data if log_data else ""
    try:
        html_page = read_html_page_template(
            filename_html="assets/main.template.html",
            filename_css="assets/styles.css",
            filename_js="assets/includes.js"
        )
    except:
        return func.HttpResponse(
            "ERROR: Couldnt read html template file assets/main.template.html or assets/styles.css",
            status_code=500
        )
    html_page = replace_and_format_html_template(html_page, replace_data)

    return func.HttpResponse(html_page, mimetype="text/html", status_code=200)
    # return func.HttpResponse(
    #     "Its folly working. Pass a name in the query string or in the request body for a personalized response.",
    #     status_code=200
    # )
