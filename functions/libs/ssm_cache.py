from aws_lambda_powertools.utilities.parameters import get_parameter

_ssm_cache = {}

def get_ssm_param(param_name):
    if param_name not in _ssm_cache:
        _ssm_cache[param_name] = get_parameter(param_name)
    return _ssm_cache[param_name] 