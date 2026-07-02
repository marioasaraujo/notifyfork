class NotificationGatewayError(Exception):
    """Base exception for the notification gateway domain."""


class NoProviderAvailable(NotificationGatewayError):
    def __init__(self, channel: str) -> None:
        super().__init__(f"No provider registered for channel: {channel}")
        self.channel = channel


class TemplateNotFound(NotificationGatewayError):
    def __init__(self, template_id: str) -> None:
        super().__init__(f"Template not found: {template_id}")
        self.template_id = template_id


class ProviderDeliveryError(NotificationGatewayError):
    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(f"Provider '{provider}' failed: {reason}")
        self.provider = provider
        self.reason = reason
