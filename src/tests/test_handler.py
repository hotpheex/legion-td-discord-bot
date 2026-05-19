"""
Characterization tests for the front-door `handler`.

These pin the *current* behaviour of the unmodified handler: Discord
ed25519 signature verification (the Discord boundary) and the pure
`discord_body` response shaper.

No test makes a real network or API call.
"""
import json
from unittest.mock import patch

import nacl.signing

from handler import main


def _signed_event(signing_key, body, timestamp="1700000000"):
    """Produce an event whose ed25519 signature is valid for `signing_key`."""
    signature = signing_key.sign(
        (timestamp + body).encode()
    ).signature.hex()
    return {
        "body": body,
        "headers": {
            "x-signature-ed25519": signature,
            "x-signature-timestamp": timestamp,
        },
    }


def test_discord_body_shape():
    response = main.discord_body(200, 2, "test message")
    assert response == {
        "statusCode": 200,
        "body": json.dumps(
            {"type": 2, "data": {"tts": False, "content": "test message"}}
        ),
    }


def test_valid_signature_accepts_correctly_signed_request():
    signing_key = nacl.signing.SigningKey.generate()
    public_key_hex = signing_key.verify_key.encode().hex()
    body = '{"type": 1}'
    event = _signed_event(signing_key, body)

    with patch.object(main, "DISCORD_PUBLIC_KEY", public_key_hex):
        assert main.valid_signature(event) is True


def test_valid_signature_rejects_tampered_body():
    signing_key = nacl.signing.SigningKey.generate()
    public_key_hex = signing_key.verify_key.encode().hex()
    event = _signed_event(signing_key, '{"type": 1}')
    # Tamper with the body after signing -> signature no longer matches.
    event["body"] = '{"type": 2}'

    with patch.object(main, "DISCORD_PUBLIC_KEY", public_key_hex):
        assert main.valid_signature(event) is False


def test_valid_signature_rejects_garbage_signature():
    signing_key = nacl.signing.SigningKey.generate()
    public_key_hex = signing_key.verify_key.encode().hex()
    event = _signed_event(signing_key, '{"type": 1}')
    # 64-byte hex string that is not a valid signature for this message.
    event["headers"]["x-signature-ed25519"] = "00" * 64

    with patch.object(main, "DISCORD_PUBLIC_KEY", public_key_hex):
        assert main.valid_signature(event) is False
