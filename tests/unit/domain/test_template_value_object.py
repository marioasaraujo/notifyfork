import pytest
from notifyfork.core.domain.value_objects.template import (
    NotificationTemplate,
    TemplateMode,
    VariableMapping,
)


class TestLocalTemplate:
    def test_renders_body_with_context(self, otp_template):
        result = otp_template.render({"code": "999888"})
        assert result == "Your code is: 999888"

    def test_renders_subject_with_context(self, email_template):
        result = email_template.render_subject({"order_id": "ORD-42", "total": "R$ 100"})
        assert result == "Order ORD-42 confirmed"

    def test_raises_on_missing_variable(self, otp_template):
        with pytest.raises(ValueError, match="Missing template variable"):
            otp_template.render({})

    def test_returns_none_subject_when_not_set(self, otp_template):
        assert otp_template.render_subject({}) is None

    def test_template_is_immutable(self, otp_template):
        with pytest.raises(Exception):
            otp_template.body = "changed"

    def test_is_not_external_by_default(self, otp_template):
        assert otp_template.is_external is False

    def test_external_template_id_raises_on_local(self, otp_template):
        with pytest.raises(ValueError, match="EXTERNAL mode"):
            _ = otp_template.external_template_id

    def test_render_raises_on_external_template(self):
        template = NotificationTemplate(
            id="wa_otp",
            body="HXabc123",
            mode=TemplateMode.EXTERNAL,
        )
        with pytest.raises(ValueError, match="EXTERNAL mode"):
            template.render({"code": "123"})


class TestExternalTemplate:
    def test_is_external(self):
        template = NotificationTemplate(
            id="wa_otp",
            body="HXabc123",
            mode=TemplateMode.EXTERNAL,
        )
        assert template.is_external is True

    def test_external_template_id_returns_body(self):
        template = NotificationTemplate(
            id="wa_otp",
            body="HXabc123",
            mode=TemplateMode.EXTERNAL,
        )
        assert template.external_template_id == "HXabc123"

    def test_sendgrid_external_template_id(self):
        template = NotificationTemplate(
            id="order_confirmed",
            body="d-abc123def456",
            mode=TemplateMode.EXTERNAL,
        )
        assert template.external_template_id == "d-abc123def456"


class TestVariableMapping:
    def test_translates_keys(self):
        mapping = VariableMapping({"name": "1", "code": "2"})
        result = mapping.translate({"name": "Mario", "code": "847291"})
        assert result == {"1": "Mario", "2": "847291"}

    def test_passthrough_when_no_mapping(self):
        mapping = VariableMapping()
        context = {"name": "Mario", "code": "123"}
        assert mapping.translate(context) == context

    def test_unmapped_keys_pass_through(self):
        mapping = VariableMapping({"name": "1"})
        result = mapping.translate({"name": "Mario", "extra": "value"})
        assert result == {"1": "Mario", "extra": "value"}

    def test_sendgrid_named_mapping(self):
        mapping = VariableMapping({
            "order_id": "order_id",
            "total": "order_total",
            "name": "customer_name",
        })
        result = mapping.translate({
            "order_id": "ORD-1",
            "total": "R$100",
            "name": "Mario",
        })
        assert result == {
            "order_id": "ORD-1",
            "order_total": "R$100",
            "customer_name": "Mario",
        }


class TestTemplateTranslateVariables:
    def test_translate_whatsapp_positional(self):
        template = NotificationTemplate(
            id="wa_otp",
            body="HXabc123",
            mode=TemplateMode.EXTERNAL,
            variable_mapping=VariableMapping({"name": "1", "code": "2"}),
        )
        result = template.translate_variables({"name": "Mario", "code": "847291"})
        assert result == {"1": "Mario", "2": "847291"}

    def test_translate_sendgrid_named(self):
        template = NotificationTemplate(
            id="order_email",
            body="d-abc123",
            mode=TemplateMode.EXTERNAL,
            variable_mapping=VariableMapping({"total": "order_total", "name": "customer_name"}),
        )
        result = template.translate_variables({"total": "R$100", "name": "Mario"})
        assert result == {"order_total": "R$100", "customer_name": "Mario"}

    def test_no_mapping_returns_context_as_is(self):
        template = NotificationTemplate(
            id="plain",
            body="d-xyz",
            mode=TemplateMode.EXTERNAL,
        )
        context = {"foo": "bar"}
        assert template.translate_variables(context) == context
