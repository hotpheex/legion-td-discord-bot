import pytest


from handler.main import *


class TestHandler:
    def test_valid_signature(self):
        assert run("event", "context") == "something"
