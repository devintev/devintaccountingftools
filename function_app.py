import azure.functions as func
import logging
from json2html import json2html
# import traceback
import sys
# import json
from datetime import datetime

from libraries import common, DLogger

# from hrmlib.hrmtools import (
#     SecretsAndSettingsManager, HTMLListHandler,
#     read_html_page_template,
#     extract_data_from_received_http_request,
#     replace_and_format_html_template
# )


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

    # html_log_handler = HTMLListHandler()
    # html_log_handler.setLevel(logging.DEBUG)
    # logger.addHandler(html_log_handler)

    print_log_handler = logging.StreamHandler()  # StreamHandler prints to console
    # Set the print handler level to ERROR
    print_log_handler.setLevel(logging.ERROR)
    logger.addHandler(print_log_handler)

    logger.debug(
        f'Python HTTP trigger received a request and started running with python version: {str(sys.version)}.')

    logging.info(
        'Python HTTP triggered ????? function starts processing a request.')

    dc = common.DevIntConnector()
    dc.setup()
    # data = dc.analyse_received_http_request(req)

    # http_vars = extract_data_from_received_http_request(
    #     http_request=req, parent_logger=logger)
    # logger.debug(f"http_vars: {json2html.convert(json = http_vars)}")
    # config = SecretsAndSettingsManager(parent_logger=logger)

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
            "Its folly working. Pass a name in the query string or in the request body for a personalized response.",
            status_code=200
        )
