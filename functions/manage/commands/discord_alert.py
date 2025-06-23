def discord_alert(body, logger=None, discord=None, context=None, **kwargs):
    # Send an alert to Discord webhook
    alert_webhook = kwargs.get('alert_webhook')
    if not alert_webhook:
        import os
        from aws_lambda_powertools.utilities.parameters import get_parameter
        alert_webhook = get_parameter(os.environ["ALERT_WEBHOOK_PARAM"])
    try:
        discord.exception_alert(alert_webhook, context)
        return ":warning: Exception alert sent to Discord."
    except Exception as e:
        if logger:
            logger.exception(e)
        return f":x: Failed to send Discord alert: {e}" 