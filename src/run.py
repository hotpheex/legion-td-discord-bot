from handler import main


def lambda_handler(event, context):
    return main.run(event, context)
