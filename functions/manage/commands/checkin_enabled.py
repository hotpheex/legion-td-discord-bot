def checkin_enabled(body, client=None, **kwargs):
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
    desired_status = body["data"]["options"][0]["options"][0]["value"]
    if current_status == desired_status:
        return f"Checkins already set to `{current_status}`"
    else:
        response = client.put_parameter(
            Name=checkin_status_param, Value=str(desired_status).lower(), Overwrite=True
        )
        return f"Checkins are now set to `{desired_status}`" 