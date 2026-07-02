from unittest.mock import MagicMock, patch

import pytest

from notifyfork.client import send


class TestSend:
    def test_enqueues_task_with_given_payload(self):
        with patch("notifyfork.client.dispatch_notification") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-1")
            result = send(
                recipient="+5511999990001",
                channel="sms",
                template_id="otp_sms",
                notification_type="transactional",
                context={"code": "123456"},
            )

        assert result.id == "task-1"
        payload = mock_task.delay.call_args[0][0]
        assert payload["channel"] == "sms"
        assert payload["template_id"] == "otp_sms"
        assert payload["recipient"] == "+5511999990001"
        assert payload["context"] == {"code": "123456"}
        assert payload["max_attempts"] == 3

    def test_defaults_context_to_empty_dict(self):
        with patch("notifyfork.client.dispatch_notification") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-3")
            send(
                recipient="+5511999990001",
                channel="sms",
                template_id="otp_sms",
                notification_type="transactional",
            )

        payload = mock_task.delay.call_args[0][0]
        assert payload["context"] == {}

    def test_blank_recipient_raises(self):
        with pytest.raises(ValueError):
            send(
                recipient="   ",
                channel="sms",
                template_id="otp_sms",
                notification_type="transactional",
            )

    def test_max_attempts_out_of_range_raises(self):
        with pytest.raises(ValueError):
            send(
                recipient="+5511999990001",
                channel="sms",
                template_id="otp_sms",
                notification_type="transactional",
                max_attempts=10,
            )

    def test_importable_from_top_level_package(self):
        import notifyfork

        assert notifyfork.send is send
