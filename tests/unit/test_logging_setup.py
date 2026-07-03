import json
import logging
import sys

from notifyfork.shared.logging.setup import JSONFormatter, setup_logging


def make_record(**extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="notifyfork.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestJSONFormatter:
    def test_formats_basic_fields_as_json(self):
        record = make_record()
        output = json.loads(JSONFormatter().format(record))

        assert output["severity"] == "INFO"
        assert output["message"] == "hello world"
        assert output["logger"] == "notifyfork.test"
        assert "timestamp" in output

    def test_includes_extra_fields(self):
        record = make_record(notification_id="abc-123")
        output = json.loads(JSONFormatter().format(record))

        assert output["notification_id"] == "abc-123"

    def test_includes_exception_when_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = make_record()
            record.exc_info = sys.exc_info()

        output = json.loads(JSONFormatter().format(record))

        assert "exception" in output
        assert "boom" in output["exception"]


class TestSetupLogging:
    def test_configures_root_logger_with_json_handler(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        try:
            for handler in original_handlers:
                root.removeHandler(handler)

            setup_logging(level="DEBUG")

            assert root.level == logging.DEBUG
            assert len(root.handlers) == 1
            assert isinstance(root.handlers[0].formatter, JSONFormatter)
        finally:
            for handler in root.handlers[:]:
                root.removeHandler(handler)
            for handler in original_handlers:
                root.addHandler(handler)
            root.setLevel(original_level)
