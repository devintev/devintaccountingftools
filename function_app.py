import azure.functions as func
import logging
from json2html import json2html
import traceback
import sys
import json
from datetime import datetime


from hrmlib.hrmtools import (
    SecretsAndSettingsManager, HTMLListHandler,
    read_html_page_template,
    extract_data_from_received_http_request,
    replace_and_format_html_template
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="test")
def test(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

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
            "Its fally working. Pass a name in the query string or in the request body for a personalized response.",
            status_code=200
        )
