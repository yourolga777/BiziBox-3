import logging

from app.utils.log_scrubber import SensitiveFilter, mask_sensitive


class TestMasking:
    def test_dict_with_sensitive_keys_is_masked(self):
        result = mask_sensitive({
            "username": "admin",
            "password": "secret123",
            "api_hash": "abc123hash",
            "session_string": "ss_token_xyz",
        })
        assert result == {
            "username": "admin",
            "password": "***",
            "api_hash": "***",
            "session_string": "***",
        }

    def test_nested_dict_with_sensitive_keys_is_masked(self):
        result = mask_sensitive({
            "user": {
                "name": "test",
                "password": "nested-secret",
            },
        })
        assert result == {
            "user": {
                "name": "test",
                "password": "***",
            },
        }

    def test_list_is_masked_recursively(self):
        result = mask_sensitive([
            {"name": "a", "token": "t1"},
            {"name": "b", "token": "t2"},
        ])
        assert result == [
            {"name": "a", "token": "***"},
            {"name": "b", "token": "***"},
        ]

    def test_non_dict_is_unchanged(self):
        assert mask_sensitive("hello") == "hello"
        assert mask_sensitive(42) == 42
        assert mask_sensitive(None) is None


class TestSensitiveFilter:
    def test_filter_masks_dict_message(self):
        f = SensitiveFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg={"password": "pwd", "data": "ok"}, args=(),
            exc_info=None,
        )
        assert f.filter(record) is True
        assert record.msg == {"password": "***", "data": "ok"}


def test_setup_logging_configures_access_and_filter():
    import inspect

    from app.utils.logger import setup_logging
    src = inspect.getsource(setup_logging)
    assert "uvicorn.access" in src
    assert "SensitiveFilter" in src
    assert "logging.INFO" in src or "INFO" in src
    assert "addFilter" in src
