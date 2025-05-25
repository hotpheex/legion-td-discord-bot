# import json
# import os
# from unittest.mock import patch
# import pytest

# import nacl.signing
# from nacl.encoding import HexEncoder
# from nacl.exceptions import BadSignatureError
# from nacl.public import PrivateKey
# import boto3

# from handler import main


# private_key = PrivateKey.generate()

# event = {
#     "body": "",
#     "headers": {"x-signature-ed25519": "", "x-signature-timestamp": ""},
# }


# @pytest.fixture(autouse=True)
# def env_setup(monkeypatch):
#     monkeypatch.setenv("DISCORD_PUBLIC_KEY", hex(private_key.public_key))
#     monkeypatch.setenv("LAMBDA_CHECKIN", "lambda_checkin")
#     monkeypatch.setenv("LAMBDA_MANAGE", "lambda_manage")
#     monkeypatch.setenv("LAMBDA_RESULTS", "lambda_results")
#     monkeypatch.setenv("ALERT_WEBHOOK", "WEBHOOK")


# def test_valid_signature():
#     body = '{"type": 1}'
#     event["body"] = body
#     signed_message = (event["headers"]["x-signature-timestamp"] + body).encode()
#     vk = nacl.signing.VerifyKey(os.environ["DISCORD_PUBLIC_KEY"], encoder=HexEncoder)
#     signature = vk.sign(signed_message).signature.hex()
#     event["headers"]["x-signature-ed25519"] = signature
#     valid = main.run.valid_signature(event)
#     assert valid == True


# def test_invalid_signature():
#     body = '{"type": 1}'
#     event["body"] = body
#     event["headers"]["x-signature-ed25519"] = "invalid_signature"
#     valid = main.run.valid_signature(event)
#     assert valid == False


# def test_discord_body():
#     message = "test message"
#     response = main.run.discord_body(200, 2, message)
#     expected_response = {
#         "statusCode": 200,
#         "body": json.dumps({"type": 2, "data": {"tts": False, "content": message}}),
#     }
#     assert response == expected_response


# @patch.dict(os.environ, {"DEBUG": "true"})
# def test_logging_debug_level():
#     assert main.run.logging.getLogger().getEffectiveLevel() == 10


# @patch.dict(os.environ, {"DEBUG": "false"})
# def test_logging_info_level():
#     assert main.run.logging.getLogger().getEffectiveLevel() == 20


# @patch("boto3.client")
# def test_invoke_lambda(mocked_lambda_client):
#     event["body"] = '{"type": 2, "data": {"name": "manage"}}'
#     command_func = "lambda_manage"
#     response = {"StatusCode": 202}
#     mocked_lambda_client.return_value.invoke.return_value = response
#     result = main.run.run(event, None)
#     mocked_lambda_client.assert_called_once()
#     mocked_lambda_client.assert_called_with("lambda")
#     assert result["statusCode"] == 200
#     assert result["body"] == json.dumps(
#         {"type": 5, "data": {"tts": False, "content": "processing"}}
#     )


# def test_handle_signup_command():
#     event["body"] = '{"type": 2, "data": {"name": "signup"}}'
#     result = main.run.run(event, None)
#     assert result["statusCode"] == 200
#     assert "FAQ" in result["body"]


# def test_handle_invalid_command():
#     event["body"] = '{"type": 2, "data": {"name": "invalid_command"}}'
#     result = main.run.run(event, None)
#     assert result["statusCode"] == 200
#     assert "Unable to" in result["body"]


# def test_handle_type1_command():
#     event["body"] = '{"type": 1}'
#     result = main.run.run(event, None)
#     assert result["statusCode"] == 200
#     assert result["body"] == json.dumps({"type": 1})
