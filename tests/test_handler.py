import pytest


from src.handler.main import run


class TestHandler:
    def test_1():
        assert run("asdf", "zxcv") == 2
