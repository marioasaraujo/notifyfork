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

Most systems start with a direct Twilio call somewhere in the codebase. Then another one. Then retry logic gets duplicated. Then someone needs WhatsApp and the whole thing breaks apart.

NotifyFork solves this by treating notifications as a **delivery problem, not a provider problem**.

You already know the channel and template you want to send. NotifyFork picks the right provider for that channel, enqueues the delivery, retries on failure, and logs everything as structured JSON, ready for GCP Cloud Logging or any aggregator.

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

That's the full API surface for the caller. Provider selection, template rendering, and retry all happen behind the queue.

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

Multiple email providers registered at once fall back on each other automatically. See "Reliability" below.

Adding a new provider = one new class. Nothing else changes.

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

**From the same project that installed NotifyFork**: call it directly in Python, no HTTP needed:

```python
import notifyfork

notifyfork.send(
    recipient="+5511999999999",
    channel="sms",
    template_id="otp_sms",
    notification_type="transactional",
    context={"code": "847291"},
)
# → enqueues to Celery, returns an AsyncResult
```

**From a different service** (another microservice, a different language): NotifyFork
deliberately doesn't ship a public HTTP endpoint. An open "send anything" endpoint
needs authentication, and that's different for every deployment, not something a
library should decide for you. Add a thin view in your own project instead:

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

Now other services can POST to whatever URL and auth scheme you chose. You're in
control of the contract, NotifyFork just does the delivery behind it.

Only the delivery-status webhooks (`notifyfork.api.webhooks`) are meant to be mounted
directly: those validate the provider's own signature (Twilio, SendGrid, Resend), so
they don't need your app's auth.

---

### Adding a new provider

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

Register it in `notifyfork/core/infrastructure/container/providers.py`, one block. Done.

If the provider lives outside the lib (a separate package, an internal-only
integration you don't want to upstream), skip editing the container and
register it with the `@notifyfork.provider` decorator instead — no
subclassing required, it's duck-typed like everything else:

```python
import notifyfork

@notifyfork.provider
class XptoProvider:
    name = "xpto"

    async def send_with_template(self, recipient, template, context):
        ...
```

The class is instantiated with no arguments and appended to
`Container.providers()`. See [`examples/custom_provider`](examples/custom_provider).

`channel` isn't a closed enum either — it's whatever string your provider's
`supported_channels` declares and your `send()` calls use. Registering a
provider for a channel NotifyFork doesn't ship (Telegram, say) works the
same as a built-in one, no core code to touch:

```python
@notifyfork.provider
class TelegramProvider:
    name = "telegram_bot"
    supported_channels = ["telegram"]

    def supports(self, channel):
        return channel in self.supported_channels

    async def send_with_template(self, recipient, template, context):
        ...

notifyfork.send(recipient="@someone", channel="telegram", template_id="greeting", notification_type="transactional")
```

---

### Adding a new kind of notification

There's no event catalog to register. Pick a `channel`, write a template
via migration, and call `notifyfork.send(...)` with that `template_id`.
Done — see [Sending a notification](#sending-a-notification) above.

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

A maioria dos sistemas começa com uma chamada direta ao Twilio em algum lugar do código. Depois vem outra. A lógica de retry fica duplicada. Alguém precisa de WhatsApp e tudo desmorona.

O NotifyFork resolve isso tratando notificações como um **problema de entrega, não de provider**.

Você já sabe qual canal e template quer usar. O NotifyFork escolhe o provider certo pra esse canal, enfileira o envio, faz retry em caso de falha, e loga tudo em JSON estruturado, pronto para GCP Cloud Logging ou qualquer agregador.

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

Essa é toda a superfície de API para quem chama. Seleção de provider, renderização de template e retry acontecem atrás da fila.

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

Registrando mais de um provider de e-mail ao mesmo tempo, o fallback entre eles acontece automático. Veja "Confiabilidade" mais abaixo.

Adicionar um novo provider = criar uma nova classe. Nada mais muda.

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

**Do mesmo projeto que instalou o NotifyFork**: chama direto em Python, sem HTTP:

```python
import notifyfork

notifyfork.send(
    recipient="+5511999999999",
    channel="sms",
    template_id="otp_sms",
    notification_type="transactional",
    context={"code": "847291"},
)
# → enfileira no Celery, retorna um AsyncResult
```

**De outro serviço** (outro microserviço seu, outra linguagem): o NotifyFork
propositalmente não expõe endpoint HTTP público. Um endpoint aberto de "manda
qualquer coisa" precisa de autenticação, e isso muda por deploy, não é algo que
uma lib deveria decidir por você. Em vez disso, crie uma view fina no seu próprio
projeto:

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

Agora outros serviços podem mandar POST pra URL e com o esquema de auth que você
escolheu. Você controla o contrato, o NotifyFork só cuida do envio por trás.

Só os webhooks de confirmação de entrega (`notifyfork.api.webhooks`) são feitos pra
montar direto: esses validam a assinatura do próprio provider (Twilio, SendGrid,
Resend), então não dependem da auth da sua aplicação.

---

### Adicionando um novo provider

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

Registre no container em `notifyfork/core/infrastructure/container/providers.py`. Pronto.

Se o provider vive fora da lib (um pacote separado, uma integração interna
que você não quer subir pro repo), não precisa mexer no container — registre
com o decorator `@notifyfork.provider`, sem precisar herdar de nada, duck-typing
igual o resto:

```python
import notifyfork

@notifyfork.provider
class XptoProvider:
    name = "xpto"

    async def send_with_template(self, recipient, template, context):
        ...
```

A classe é instanciada sem argumentos e adicionada em `Container.providers()`.
Veja [`examples/custom_provider`](examples/custom_provider).

`channel` também não é um enum fechado — é a string que o `supported_channels`
do seu provider declarar e que você usar na chamada de `send()`. Registrar um
provider pra um canal que o NotifyFork não vem com suporte nativo (Telegram,
por exemplo) funciona igual a um built-in, sem tocar em código do core:

```python
@notifyfork.provider
class TelegramProvider:
    name = "telegram_bot"
    supported_channels = ["telegram"]

    def supports(self, channel):
        return channel in self.supported_channels

    async def send_with_template(self, recipient, template, context):
        ...

notifyfork.send(recipient="@someone", channel="telegram", template_id="greeting", notification_type="transactional")
```

---

### Adicionando um novo tipo de notificação

Não existe catálogo de eventos pra cadastrar. Escolhe um `channel`, cria o
template via migration, e chama `notifyfork.send(...)` com esse `template_id`.
Pronto — veja [Enviando uma notificação](#enviando-uma-notificação) acima.

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
│   ├── api/                   ← Views Django, serializers, event router, webhooks
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
