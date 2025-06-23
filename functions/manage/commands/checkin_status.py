def checkin_status(body, client=None, **kwargs):
    checkin_status_param = kwargs.get('checkin_status_param')
    if not checkin_status_param and 'CHECKIN_STATUS_PARAM' in kwargs:
        checkin_status_param = kwargs['CHECKIN_STATUS_PARAM']
    elif not checkin_status_param:
        checkin_status_param = None
    # Fallback to environment if not provided
    if not checkin_status_param:
        import os
        checkin_status_param = os.environ.get('CHECKIN_STATUS_PARAM')
    response = client.get_parameter(Name=checkin_status_param)
    current_status = response["Parameter"]["Value"]
    return f"Checkins are currently set to `{current_status}`" 