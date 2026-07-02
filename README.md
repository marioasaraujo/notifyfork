<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:2c5364&height=100&section=header&animation=fadeIn"/>

<h1>📡 NotifyFork</h1>

<p><strong>Provider-agnostic notification gateway for Django.</strong><br/>
One API. Any channel. Send to SMS, Email, WhatsApp, Push, and Slack,<br/>
delivered asynchronously, retried safely, logged in structured JSON.</p>

[![PyPI version](https://img.shields.io/pypi/v/notifyfork?style=flat-square&color=2c5364)](https://pypi.org/project/notifyfork)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django)](https://djangoproject.com)
[![Celery](https://img.shields.io/badge/Celery-5.x-37814A?style=flat-square&logo=celery)](https://docs.celeryq.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)

**[English](#english) · [Português](#português)**

</div>

---

<a name="english"></a>
## 🇬🇧 English

### What is NotifyFork?

Direct Twilio calls scattered through a codebase get messy fast: duplicated retry logic, then someone needs WhatsApp and it all falls apart.

NotifyFork is a thin, provider-agnostic delivery layer. You already know the channel and template you want; it picks the right provider, enqueues the delivery, retries on failure, and logs everything as structured JSON.

```bash
pip install notifyfork
```

```python
import notifyfork

notifyfork.send(
    recipient="+5511999999999",
    channel="sms",
    template_id="otp_sms",
    notification_type="transactional",
    context={"code": "847291"},
)
# → enqueued to Celery, retried on failure
```

That's the whole API. Provider selection, template rendering, and retry all happen behind the queue.

---

### Channels & providers

| Channel | Provider | Template mode |
|---------|----------|---------------|
| SMS | Twilio | Local (free-form text) |
| Email | SendGrid | Local **or** External (Dynamic Templates) |
| Email | Resend | Local (HTML rendered here) |
| Email | SMTP (any server) | Local (HTML rendered here) |
| WhatsApp | Twilio | Local (sandbox) **or** External (Content Templates) |
| Push | Firebase Cloud Messaging | Local (title + body) |
| Slack | Slack Web API | Local (plain or Block Kit) |

Multiple providers per channel fall back on each other automatically (see "Reliability"). Adding a provider is one new class — see "Adding a provider" below. `channel` isn't limited to this table either; you can register a provider for a channel NotifyFork doesn't ship at all.

---

### Template modes

**LOCAL**: body is rendered here using Python's `string.Template`.

```python
body = "Your code is: $code"
context = {"code": "847291"}
# → "Your code is: 847291"
```

**EXTERNAL**: body is the provider's template ID. Variables translated via `VariableMapping` before dispatch.

```python
# SendGrid Dynamic Template
body = "d-abc123def456"
variable_mapping = {"name": "customer_name", "total": "order_total"}

# Twilio WhatsApp Content Template (positional)
body = "HXabc123def456"
variable_mapping = {"name": "1", "code": "2"}
```

---

### Architecture

```
notifyfork.send()  (or your own view calling it)
        │
        ▼
  Celery Queue         ← async, acks_late, exponential backoff
        │
        ▼
  SendNotificationUseCase
  ├── TemplateRepository    ← loads template + variable mapping
  ├── ProviderRegistry      ← picks provider by channel
  └── NotificationRepository ← persists state transitions

  State: PENDING → QUEUED → SENT
                          ↘ RETRYING (attempt 1, 2...)
                                    ↘ FAILED
```

The domain layer has **zero imports from providers or Django**. Swap PostgreSQL, change Celery to SQS, replace Twilio: the core logic stays untouched.

---

### Getting started

```bash
pip install notifyfork
```

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "notifyfork.core.infrastructure",
]
```

```python
# urls.py (optional, only needed to receive provider delivery webhooks)
urlpatterns = [
    ...,
    path("api/v1/", include("notifyfork.api.urls")),
]
```

```bash
cp .env.example .env  # fill in your provider credentials
python manage.py migrate
celery -A yourproject worker --loglevel=info   # your own Celery app, autodiscovers NotifyFork's tasks
```

Then try it with any of the [runnable examples](examples/) via `python manage.py shell`.

---

### Sending a notification

**Same project**: call `notifyfork.send(...)` directly in Python, as shown above. No HTTP needed.

**Different service** (another microservice, another language): NotifyFork doesn't ship a public HTTP endpoint on purpose — auth is different per deployment, not something a library should decide for you. Add a thin authenticated view instead:

```python
# yourproject/notifications/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # or whatever auth you use
import notifyfork

class SendNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        task = notifyfork.send(
            recipient=request.data["recipient"],
            channel=request.data["channel"],
            template_id=request.data["template_id"],
            notification_type=request.data["notification_type"],
            context=request.data.get("context", {}),
        )
        return Response({"task_id": task.id}, status=202)
```

Other services POST to whatever URL and auth scheme you chose — you control the contract, NotifyFork just does the delivery behind it.

The delivery-status webhooks (`notifyfork.api.webhooks`) are the one exception meant to be mounted directly: they validate the provider's own signature (Twilio, SendGrid, Resend), so they don't need your app's auth.

---

### Adding a provider

**Built into the lib** — subclass `NotificationProvider` and register it in `container/providers.py`:

```python
# notifyfork/core/infrastructure/providers/my_provider.py
class MyProvider(NotificationProvider):
    @property
    def name(self) -> str:
        return "my_provider"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        return [NotificationChannel.SMS]

    async def send_with_template(self, recipient, template, context) -> ProviderResult:
        body = template.render(context)
        # your API call here
        ...
```

**From your own project** — no subclassing, no editing the container, just decorate a plain class (duck-typed, only `.name` and `.send_with_template()` are ever touched):

```python
import notifyfork

@notifyfork.provider
class TelegramProvider:
    name = "telegram_bot"
    supported_channels = ["telegram"]  # channel isn't a closed enum — any string works

    def supports(self, channel):
        return channel in self.supported_channels

    async def send_with_template(self, recipient, template, context):
        ...

notifyfork.send(recipient="@someone", channel="telegram", template_id="greeting", notification_type="transactional")
```

The class is instantiated with no arguments and appended to `Container.providers()`. See [`examples/custom_provider`](examples/custom_provider).

---

### Adding a kind of notification

No event catalog to register. Pick a `channel`, write a template via migration, call `notifyfork.send(...)` with that `template_id`. Done.

---

### Reliability

- **Exponential backoff**: 60s → 120s → 240s, capped at 10 minutes
- **`acks_late=True`**: task only acknowledged after completion; safe on worker crash
- **Beat sweep**: periodic task re-queues notifications stuck in `RETRYING`
- **N+1 safe**: all queries are bounded with `LIMIT`
- **Provider fallback**: if you register more than one provider for the same
  channel (e.g. SendGrid + SMTP for email), a failure on the first one falls
  through to the next immediately, no wait for the retry backoff. Order is
  explicit, not whatever `Container.providers()` happened to build first:
  defaults to `DEFAULT_PROVIDER_ORDER` in `container/providers.py`, override
  with `NOTIFYFORK_PROVIDER_ORDER=sendgrid_email,smtp_email`. Whichever
  provider actually sent it is always recorded in `notification.provider_used`.

---

### Running tests

```bash
pytest tests/unit -v --cov=notifyfork
# Coverage gate: 80% minimum, see CONTRIBUTING.md
```

---

<a name="português"></a>
## 🇧🇷 Português

### O que é o NotifyFork?

Chamada direta ao Twilio espalhada pelo código vira bagunça rápido: lógica de retry duplicada, e daí alguém precisa de WhatsApp e tudo desmorona.

O NotifyFork é uma camada de entrega fina e agnóstica de provider. Você já sabe qual canal e template quer usar; ele escolhe o provider certo, enfileira o envio, faz retry em caso de falha, e loga tudo em JSON estruturado.

```bash
pip install notifyfork
```

```python
import notifyfork

notifyfork.send(
    recipient="+5511999999999",
    channel="sms",
    template_id="otp_sms",
    notification_type="transactional",
    context={"code": "847291"},
)
# → enfileirado no Celery, com retry em caso de falha
```

Essa é toda a API. Seleção de provider, renderização de template e retry acontecem atrás da fila.

---

### Canais e providers

| Canal | Provider | Modo de template |
|-------|----------|-----------------|
| SMS | Twilio | Local (texto livre) |
| E-mail | SendGrid | Local **ou** Externo (Dynamic Templates) |
| E-mail | Resend | Local (HTML renderizado aqui) |
| E-mail | SMTP (qualquer servidor) | Local (HTML renderizado aqui) |
| WhatsApp | Twilio | Local (sandbox) **ou** Externo (Content Templates) |
| Push | Firebase Cloud Messaging | Local (título + body) |
| Slack | Slack Web API | Local (texto simples ou Block Kit) |

Mais de um provider por canal cai um pro outro automaticamente (veja "Confiabilidade"). Adicionar um provider é uma classe nova — veja "Adicionando um provider" abaixo. `channel` também não fica preso a essa tabela; dá pra registrar um provider pra um canal que o NotifyFork nem conhece.

---

### Modos de template

**LOCAL**: o body é renderizado aqui usando `string.Template` do Python.

```python
body = "Seu código é: $code"
context = {"code": "847291"}
# → "Seu código é: 847291"
```

**EXTERNO**: o body é o ID do template no provider. As variáveis são traduzidas via `VariableMapping` antes do envio.

```python
# SendGrid Dynamic Template
body = "d-abc123def456"
variable_mapping = {"name": "customer_name", "total": "order_total"}

# Twilio WhatsApp Content Template (posicional)
body = "HXabc123def456"
variable_mapping = {"name": "1", "code": "2"}
```

---

### Começando

```bash
pip install notifyfork
```

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "notifyfork.core.infrastructure",
]
```

```python
# urls.py (opcional, só necessário pra receber os webhooks de entrega dos providers)
urlpatterns = [
    ...,
    path("api/v1/", include("notifyfork.api.urls")),
]
```

```bash
cp .env.example .env  # preencha as credenciais dos providers que vai usar
python manage.py migrate
celery -A seuprojeto worker --loglevel=info   # seu próprio Celery, descobre as tasks do NotifyFork
```

Depois é só testar com um dos [exemplos executáveis](examples/) via `python manage.py shell`.

---

### Enviando uma notificação

**Mesmo projeto**: chama `notifyfork.send(...)` direto em Python, como no exemplo acima. Sem HTTP.

**Outro serviço** (outro microserviço seu, outra linguagem): o NotifyFork propositalmente não expõe endpoint HTTP público — auth muda por deploy, não é algo que uma lib deveria decidir por você. Em vez disso, crie uma view fina e autenticada no seu próprio projeto:

```python
# seuprojeto/notifications/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # ou a auth que você usa
import notifyfork

class SendNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        task = notifyfork.send(
            recipient=request.data["recipient"],
            channel=request.data["channel"],
            template_id=request.data["template_id"],
            notification_type=request.data["notification_type"],
            context=request.data.get("context", {}),
        )
        return Response({"task_id": task.id}, status=202)
```

Outros serviços mandam POST pra URL e esquema de auth que você escolheu — você controla o contrato, o NotifyFork só cuida do envio por trás.

Os webhooks de confirmação de entrega (`notifyfork.api.webhooks`) são a única exceção feita pra montar direto: eles validam a assinatura do próprio provider (Twilio, SendGrid, Resend), então não dependem da auth da sua aplicação.

---

### Adicionando um provider

**Dentro da lib** — herda de `NotificationProvider` e registra no `container/providers.py`:

```python
class MeuProvider(NotificationProvider):
    @property
    def name(self) -> str:
        return "meu_provider"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        return [NotificationChannel.SMS]

    async def send_with_template(self, recipient, template, context) -> ProviderResult:
        body = template.render(context)
        # sua chamada de API aqui
        ...
```

**Do seu próprio projeto** — sem herdar nada, sem mexer no container, só decora uma classe comum (duck-typing, só `.name` e `.send_with_template()` são usados):

```python
import notifyfork

@notifyfork.provider
class TelegramProvider:
    name = "telegram_bot"
    supported_channels = ["telegram"]  # channel não é enum fechado, qualquer string serve

    def supports(self, channel):
        return channel in self.supported_channels

    async def send_with_template(self, recipient, template, context):
        ...

notifyfork.send(recipient="@someone", channel="telegram", template_id="greeting", notification_type="transactional")
```

A classe é instanciada sem argumentos e adicionada em `Container.providers()`.
Veja [`examples/custom_provider`](examples/custom_provider).

---

### Adicionando um tipo de notificação

Não existe catálogo de eventos. Escolhe um `channel`, cria o template via migration, chama `notifyfork.send(...)` com esse `template_id`. Pronto.

---

### Confiabilidade

- **Backoff exponencial**: 60s → 120s → 240s, limite de 10 minutos
- **`acks_late=True`**: task só confirmada após conclusão; seguro em caso de crash do worker
- **Sweep periódico**: task beat re-enfileira notificações travadas em `RETRYING`
- **Seguro contra N+1**: todas as queries têm `LIMIT`
- **Fallback entre providers**: se você registrar mais de um provider pro
  mesmo canal (ex: SendGrid + SMTP pra email), uma falha no primeiro cai pro
  próximo na hora, sem esperar o backoff do retry. A ordem é explícita, não é
  "o que o `Container.providers()` montou primeiro": usa `DEFAULT_PROVIDER_ORDER`
  em `container/providers.py` por padrão, dá pra sobrescrever com
  `NOTIFYFORK_PROVIDER_ORDER=sendgrid_email,smtp_email`. Qual provider
  realmente enviou fica sempre registrado em `notification.provider_used`.

---

### Rodando os testes

```bash
pytest tests/unit -v --cov=notifyfork
# Meta de cobertura: mínimo 80%, aplicado no CI
```

---

## 🗂 Estrutura do projeto

```
notifyfork/
├── notifyfork/                ← o pacote publicado (isto que vira "pip install notifyfork")
│   ├── api/                   ← Views Django, serializers, webhooks
│   └── core/
│       ├── domain/            ← Entidades, value objects, domain events
│       ├── application/       ← Use cases, interfaces, DTOs
│       └── infrastructure/    ← Providers, repositories, Celery tasks, container
├── examples/                   ← Exemplos executáveis por canal
│   ├── sms/
│   ├── email/
│   ├── whatsapp/
│   ├── push/
│   └── slack/
└── tests/
    ├── conftest.py            ← Fixtures compartilhadas
    └── unit/
```

---

## 🤝 Contributing / Contribuindo

Contributions are welcome! / Contribuições são bem-vindas!

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR
- Open an [issue](https://github.com/marioasaraujo/notifyfork/issues) to discuss new features or bugs
- PRs for new providers, bug fixes, and documentation improvements are always appreciated

---

## 📬 Contact / Contato

**Mario Araujo**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/marioasaraujo)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/marioasaraujo)
[![Email](https://img.shields.io/badge/Email-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:marioasaraujo@gmail.com)

> Found a bug? Open an [issue](https://github.com/marioasaraujo/notifyfork/issues).
> Want to collaborate or hire me for a project? Reach out on LinkedIn.

---

## 📄 License

MIT © [Mario Araujo](https://github.com/marioasaraujo)

Veja [LICENSE](LICENSE) para mais detalhes.

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:2c5364,50:203a43,100:0f2027&height=60&section=footer"/>
