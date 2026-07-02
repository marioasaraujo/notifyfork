import pytest
from notifyfork.core.application.dtos.send_notification_dto import SendNotificationDTO
from notifyfork.core.application.use_cases.send_notification import SendNotificationUseCase
from notifyfork.core.domain.entities.notification import NotificationChannel, NotificationStatus, NotificationType
from notifyfork.shared.exceptions.provider_exceptions import TemplateNotFound, NoProviderAvailable


def make_dto(channel=NotificationChannel.SMS, template_id="otp_sms", **kwargs) -> SendNotificationDTO:
    return SendNotificationDTO(
        recipient="+5511999999999",
        channel=channel,
        notification_type=NotificationType.TRANSACTIONAL,
        template_id=template_id,
        context=kwargs.get("context", {"code": "123456"}),
        max_attempts=kwargs.get("max_attempts", 3),
    )


@pytest.mark.asyncio
class TestSendNotificationUseCase:

    # Success paths

    async def test_sends_sms_successfully(
        self, mock_notification_repository, mock_template_repository, twilio_sms_provider
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_sms_provider]
        )
        notification_id = await use_case.execute(make_dto())
        assert notification_id is not None
        twilio_sms_provider.send_with_template.assert_called_once()

    async def test_sends_email_successfully(
        self, mock_notification_repository, mock_template_repository, smtp_email_provider
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [smtp_email_provider]
        )
        dto = make_dto(
            channel=NotificationChannel.EMAIL,
            template_id="order_confirmed",
            context={"order_id": "ORD-1", "total": "R$ 100"},
        )
        notification_id = await use_case.execute(dto)
        assert notification_id is not None

    async def test_sends_whatsapp_successfully(
        self, mock_notification_repository, mock_template_repository, twilio_whatsapp_provider
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_whatsapp_provider]
        )
        dto = make_dto(
            channel=NotificationChannel.WHATSAPP,
            template_id="order_shipped_wa",
            context={"tracking_code": "BR999"},
        )
        notification_id = await use_case.execute(dto)
        assert notification_id is not None

    async def test_sends_slack_alert_successfully(
        self, mock_notification_repository, mock_template_repository, slack_provider
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [slack_provider]
        )
        dto = SendNotificationDTO(
            recipient="C012AB3CD",
            channel=NotificationChannel.SLACK,
            notification_type=NotificationType.ALERT,
            template_id="system_error_slack",
            context={"service": "api", "error": "timeout"},
        )
        notification_id = await use_case.execute(dto)
        assert notification_id is not None

    async def test_sends_push_notification_successfully(
        self, mock_notification_repository, mock_template_repository, firebase_push_provider
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [firebase_push_provider]
        )
        dto = SendNotificationDTO(
            recipient="fcm-token-xyz",
            channel=NotificationChannel.PUSH,
            notification_type=NotificationType.MARKETING,
            template_id="flash_sale_push",
            context={"discount": "20%", "expires_in": "3h"},
        )
        notification_id = await use_case.execute(dto)
        assert notification_id is not None

    # State transitions

    async def test_saves_twice_queued_then_sent(
        self, mock_notification_repository, mock_template_repository, twilio_sms_provider
    ):
        # Notification is mutated in place, so call_args_list would hold two
        # references to the same final state — snapshot the status on each save instead.
        saved_statuses = []
        mock_notification_repository.save.side_effect = (
            lambda notification: saved_statuses.append(notification.status)
        )

        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_sms_provider]
        )
        await use_case.execute(make_dto())

        assert saved_statuses == [NotificationStatus.QUEUED, NotificationStatus.SENT]

    async def test_marks_failed_on_provider_error(
        self, mock_notification_repository, mock_template_repository
    ):
        from tests.conftest import make_mock_provider
        failing_provider = make_mock_provider(
            "twilio_sms", [NotificationChannel.SMS], success=False, error="connection refused"
        )
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [failing_provider]
        )
        await use_case.execute(make_dto())

        last_saved = mock_notification_repository.save.call_args_list[-1][0][0]
        assert last_saved.status in (NotificationStatus.RETRYING, NotificationStatus.FAILED)
        assert last_saved.error_detail == "connection refused"

    async def test_records_provider_name_on_success(
        self, mock_notification_repository, mock_template_repository, twilio_sms_provider
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_sms_provider]
        )
        await use_case.execute(make_dto())
        last_saved = mock_notification_repository.save.call_args_list[-1][0][0]
        assert last_saved.provider_used == "twilio_sms"

    # Error paths

    async def test_raises_template_not_found(
        self, mock_notification_repository, mock_template_repository, twilio_sms_provider
    ):
        mock_template_repository.get_by_id.return_value = None
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_sms_provider]
        )
        with pytest.raises(TemplateNotFound):
            await use_case.execute(make_dto(template_id="nonexistent"))

    async def test_raises_no_provider_for_channel(
        self, mock_notification_repository, mock_template_repository, twilio_sms_provider
    ):
        # SMS provider only — ask for email
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_sms_provider]
        )
        dto = make_dto(
            channel=NotificationChannel.EMAIL,
            template_id="order_confirmed",
            context={"order_id": "ORD-1", "total": "R$ 100"},
        )
        with pytest.raises(NoProviderAvailable):
            await use_case.execute(dto)

    async def test_does_not_save_when_template_missing(
        self, mock_notification_repository, mock_template_repository, twilio_sms_provider
    ):
        mock_template_repository.get_by_id.return_value = None
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [twilio_sms_provider]
        )
        with pytest.raises(TemplateNotFound):
            await use_case.execute(make_dto(template_id="ghost"))
        mock_notification_repository.save.assert_not_called()

    # Free-form channel / notification_type

    async def test_channel_outside_the_built_in_enum_still_works(
        self, mock_notification_repository, mock_template_repository
    ):
        """channel/notification_type are plain strings — a provider for a
        channel NotificationChannel doesn't even know about (e.g. a custom
        Telegram integration) works the same as a built-in one."""
        from tests.conftest import make_mock_provider
        telegram_provider = make_mock_provider("telegram_bot", ["telegram"])

        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [telegram_provider]
        )
        dto = make_dto(channel="telegram")
        notification_id = await use_case.execute(dto)

        assert notification_id is not None
        telegram_provider.send_with_template.assert_called_once()

    # Provider selection

    async def test_uses_first_matching_provider(
        self, mock_notification_repository, mock_template_repository, all_providers
    ):
        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, all_providers
        )
        await use_case.execute(make_dto(channel=NotificationChannel.SMS))

        sms_provider = next(p for p in all_providers if p.name == "twilio_sms")
        sms_provider.send_with_template.assert_called_once()

        # Other providers must NOT be called
        for p in all_providers:
            if p.name != "twilio_sms":
                p.send_with_template.assert_not_called()

    # Fallback between providers of the same channel

    async def test_falls_back_to_second_provider_on_failure(
        self, mock_notification_repository, mock_template_repository
    ):
        from tests.conftest import make_mock_provider

        primary = make_mock_provider(
            "sendgrid_email", [NotificationChannel.EMAIL], success=False, error="rate limited"
        )
        fallback = make_mock_provider("smtp_email", [NotificationChannel.EMAIL], success=True)

        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [primary, fallback]
        )
        dto = make_dto(
            channel=NotificationChannel.EMAIL,
            template_id="order_confirmed",
            context={"order_id": "ORD-1", "total": "R$ 100"},
        )
        await use_case.execute(dto)

        primary.send_with_template.assert_called_once()
        fallback.send_with_template.assert_called_once()

        last_saved = mock_notification_repository.save.call_args_list[-1][0][0]
        assert last_saved.status == NotificationStatus.SENT
        assert last_saved.provider_used == "smtp_email"

    async def test_does_not_try_fallback_after_success(
        self, mock_notification_repository, mock_template_repository
    ):
        from tests.conftest import make_mock_provider

        primary = make_mock_provider("sendgrid_email", [NotificationChannel.EMAIL], success=True)
        fallback = make_mock_provider("smtp_email", [NotificationChannel.EMAIL], success=True)

        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [primary, fallback]
        )
        dto = make_dto(
            channel=NotificationChannel.EMAIL,
            template_id="order_confirmed",
            context={"order_id": "ORD-1", "total": "R$ 100"},
        )
        await use_case.execute(dto)

        primary.send_with_template.assert_called_once()
        fallback.send_with_template.assert_not_called()

    async def test_marks_failed_when_all_fallbacks_fail(
        self, mock_notification_repository, mock_template_repository
    ):
        from tests.conftest import make_mock_provider

        primary = make_mock_provider(
            "sendgrid_email", [NotificationChannel.EMAIL], success=False, error="rate limited"
        )
        fallback = make_mock_provider(
            "smtp_email", [NotificationChannel.EMAIL], success=False, error="connection refused"
        )

        use_case = SendNotificationUseCase(
            mock_notification_repository, mock_template_repository, [primary, fallback]
        )
        dto = make_dto(
            channel=NotificationChannel.EMAIL,
            template_id="order_confirmed",
            context={"order_id": "ORD-1", "total": "R$ 100"},
        )
        await use_case.execute(dto)

        primary.send_with_template.assert_called_once()
        fallback.send_with_template.assert_called_once()

        last_saved = mock_notification_repository.save.call_args_list[-1][0][0]
        assert last_saved.status in (NotificationStatus.RETRYING, NotificationStatus.FAILED)
        assert last_saved.error_detail == "connection refused"
