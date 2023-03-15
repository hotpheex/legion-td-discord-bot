import traceback
import requests
import logging


class Discord:
    def __init__(self, application_id, token):
        self.application_id = application_id
        self.token = token

    def message_response(self, message):
        logging.info(f"MESSAGE: {message}")
        res = requests.patch(
            f"https://discord.com/api/webhooks/{self.application_id}/{self.token}/messages/@original",
            json={"content": message}
        )
        res.raise_for_status()
        logging.debug(res.status_code)

    def exception_alert(self, webhook, context):
        res = requests.post(
            webhook,
            json={
                "content": f"`{context.function_name} - {context.log_stream_name}`\n```{traceback.format_exc()}```"
            },
        )
        logging.debug(res.status_code)
