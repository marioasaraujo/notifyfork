from unittest.mock import MagicMock, patch

import pytest

from notifyfork.api.routing.event_router import UnroutableEvent
from notifyfork.client import send_event


class TestSendEvent:
    def test_enqueues_task_with_resolved_routing(self):
        with patch("notifyfork.client.dispatch_notification") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-1")
            result = send_event("user.otp_requested", "+5511999990001", {"code": "123456"})

        assert result.id == "task-1"
        payload = mock_task.delay.call_args[0][0]
        assert payload["channel"] == "sms"
        assert payload["template_id"] == "otp_sms"
        assert payload["recipient"] == "+5511999990001"
        assert payload["context"] == {"code": "123456"}
        assert payload["max_attempts"] == 3

    def test_normalizes_event_type(self):
        with patch("notifyfork.client.dispatch_notification") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-2")
            send_event("USER.OTP_REQUESTED", "+5511999990001")

        payload = mock_task.delay.call_args[0][0]
        assert payload["channel"] == "sms"

    def test_defaults_context_to_empty_dict(self):
        with patch("notifyfork.client.dispatch_notification") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-3")
            send_event("user.otp_requested", "+5511999990001")

        payload = mock_task.delay.call_args[0][0]
        assert payload["context"] == {}

    def test_unroutable_event_raises(self):
        with pytest.raises(UnroutableEvent):
            send_event("nonexistent.event", "+5511999990001")

    def test_blank_recipient_raises(self):
        with pytest.raises(ValueError):
            send_event("user.otp_requested", "   ")

    def test_max_attempts_out_of_range_raises(self):
        with pytest.raises(ValueError):
            send_event("user.otp_requested", "+5511999990001", max_attempts=10)

    def test_importable_from_top_level_package(self):
        import notifyfork

        assert notifyfork.send_event is send_event
