# Notifiers

A notifier delivers an alert when a pipeline status transition occurs. Each notifier is a
plugin — one file, one entry point. Failures in one notifier are isolated; they never crash
the scheduler or prevent other notifiers from running.

## `BaseNotifier` ABC

```python
# pipe_ping/notifiers/base.py
class BaseNotifier(ABC):
    @classmethod
    @abstractmethod
    def create(cls) -> "BaseNotifier": ...

    @abstractmethod
    async def notify(self, event: StatusChangeEvent) -> None: ...
```

- `create()` reads the notifier's own settings from the environment and returns a
  configured instance. Core calls this once at startup and passes the instance around.
- Receives a `StatusChangeEvent` (not a raw document) — includes old and new status
- All I/O must be async — no blocking calls, no `time.sleep()`
- Exceptions must not propagate — the scheduler catches and logs them
- See [status-detection.md](status-detection.md) for the `StatusChangeEvent` model

## Plugin Registration

All notifiers register in `pyproject.toml`:

```toml
[project.entry-points."pipe_ping.notifiers"]
desktop = "pipe_ping.notifiers.desktop:DesktopNotifier"
webhook = "pipe_ping.notifiers.webhook:WebhookNotifier"
email   = "pipe_ping.notifiers.email:EmailNotifier"
sms     = "pipe_ping.notifiers.sms:SMSNotifier"
```

---

## Desktop Notifier

**File:** `pipe_ping/notifiers/desktop.py`

**Library:** `desktop-notifier`

**Platform support:** Windows (Win32 toast), Linux (libnotify / D-Bus), macOS (UNUserNotification)

No credentials required. `create()` returns a new instance with no configuration.

**Notification content:**

- Title: `"{repo} — {previous_status} → {current_status}"`
- Body: `"Branch: {branch}\nCommit: {commit_sha[:8]}\n{url}"`

On headless systems where no display is available the plugin raises an error at load
time. The discovery function catches this and logs a warning rather than crashing.

---

## Webhook Notifier

**File:** `pipe_ping/notifiers/webhook.py`

**Library:** `aiohttp.ClientSession`

**Configuration:**

```python
class WebhookSettings(BaseSettings):
    url: str

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_WEBHOOK_",
        env_file=".env",
    )
```

| Env var | Required | Description |
| --- | --- | --- |
| `PIPE_PING_WEBHOOK_URL` | yes | URL to POST `StatusChangeEvent` JSON to |

POST the serialized `StatusChangeEvent` as JSON to the configured URL.
Treat non-2xx responses as errors (log at WARNING, do not retry).

---

## Email Notifier

**File:** `pipe_ping/notifiers/email.py`

**Library:** `aiosmtplib`

**Configuration:**

```python
class EmailSettings(BaseSettings):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_to: str

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_EMAIL_",
        env_file=".env",
    )
```

| Env var | Required | Description |
| --- | --- | --- |
| `PIPE_PING_EMAIL_SMTP_HOST` | yes | SMTP server hostname |
| `PIPE_PING_EMAIL_SMTP_PORT` | no (default `587`) | SMTP server port |
| `PIPE_PING_EMAIL_SMTP_USER` | yes | SMTP authentication username |
| `PIPE_PING_EMAIL_SMTP_PASSWORD` | yes | SMTP authentication password |
| `PIPE_PING_EMAIL_SMTP_TO` | yes | Recipient address for alert emails |

---

## SMS Notifier

**File:** `pipe_ping/notifiers/sms.py`

**Library:** Twilio Python SDK (preferred); AWS SNS as fallback

**Configuration:**

```python
class SMSSettings(BaseSettings):
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from: str
    twilio_to: str

    model_config = SettingsConfigDict(
        env_prefix="PIPE_PING_SMS_",
        env_file=".env",
    )
```

| Env var | Required | Description |
| --- | --- | --- |
| `PIPE_PING_SMS_TWILIO_ACCOUNT_SID` | yes | Twilio account SID (`ACxxx...`) |
| `PIPE_PING_SMS_TWILIO_AUTH_TOKEN` | yes | Twilio auth token |
| `PIPE_PING_SMS_TWILIO_FROM` | yes | Sender phone number in E.164 format |
| `PIPE_PING_SMS_TWILIO_TO` | yes | Recipient phone number in E.164 format |
