from dataclasses import dataclass, field
from enum import Enum
from string import Template
from typing import Any


class TemplateMode(str, Enum):
    LOCAL = "local"       # rendered here — body is the content
    EXTERNAL = "external" # rendered by provider — body is the template ID


@dataclass(frozen=True)
class VariableMapping:
    """
    Maps our semantic variable names to provider-specific keys.

    Twilio WhatsApp uses positional keys: {"name": "1", "code": "2"}
    SendGrid uses named keys: {"name": "user_name", "code": "otp_code"}
    Mailgun uses the same name: {"name": "name", "code": "code"}

    This keeps your context payload consistent regardless of provider.
    You always send {"name": "Mario", "code": "123"} and the mapping
    translates to whatever the provider expects.
    """
    mappings: dict[str, str] = field(default_factory=dict)

    def translate(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Translates context keys using the mapping.
        Keys not in the mapping are passed through as-is.
        """
        if not self.mappings:
            return context
        return {
            self.mappings.get(k, k): v
            for k, v in context.items()
        }


@dataclass(frozen=True)
class NotificationTemplate:
    """
    Unified template value object supporting local and external rendering.

    LOCAL mode:
        body is the actual content with $variable placeholders.
        Rendered here using Python's string.Template.

    EXTERNAL mode:
        body is the external template ID (e.g. Twilio SID "HXabc123",
        SendGrid ID "d-abc123", Mailgun template name "otp-email").
        variable_mapping translates our context to provider-expected keys.
        Provider receives the ID + translated variables — renders on their end.
    """

    id: str
    body: str                                          # content OR external template ID
    mode: TemplateMode = TemplateMode.LOCAL
    subject: str | None = None                        # email subject (LOCAL mode)
    variable_mapping: VariableMapping = field(default_factory=VariableMapping)

    @property
    def is_external(self) -> bool:
        return self.mode == TemplateMode.EXTERNAL

    @property
    def external_template_id(self) -> str:
        """Alias for clarity when in EXTERNAL mode."""
        if not self.is_external:
            raise ValueError("external_template_id is only valid in EXTERNAL mode")
        return self.body

    def render(self, context: dict[str, Any]) -> str:
        """Render body locally. Only valid in LOCAL mode."""
        if self.is_external:
            raise ValueError(
                "Cannot render locally — this template uses EXTERNAL mode. "
                "Pass the template to the provider directly."
            )
        try:
            return Template(self.body).substitute(context)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}") from e

    def render_subject(self, context: dict[str, Any]) -> str | None:
        if not self.subject:
            return None
        try:
            return Template(self.subject).substitute(context)
        except KeyError as e:
            raise ValueError(f"Missing subject variable: {e}") from e

    def translate_variables(self, context: dict[str, Any]) -> dict[str, Any]:
        """Translate context to provider-expected variable names."""
        return self.variable_mapping.translate(context)
