# Apprise notifications

## What is Apprise?

[Apprise](https://github.com/caronc/apprise) is an open-source notification
library that sends messages to more than 90 services through one URL format.
Nexara uses it so you can receive community notifications in the tools you
already use, such as a chat app, a phone, or a monitoring system, in addition
to in-app, Web Push, and email alerts. You add one URL per destination, and
Nexara does the rest.

## Supported services

Apprise supports far more than we can list here. Popular choices include:

| Category   | Services                                                   |
|------------|------------------------------------------------------------|
| Chat       | Slack, Discord, Microsoft Teams, Telegram, Signal          |
| Self-hosted chat | Rocket.Chat, Mattermost, Matrix                      |
| Monitoring | PagerDuty, Opsgenie, Datadog                               |
| Messaging  | Email, SMS gateways (AWS SNS, Twilio, Vonage)              |
| Push       | ntfy, Gotify, Pushover                                     |

The full, current list with the URL format for each service is in the
[official Apprise documentation](https://appriseit.com/services/) and the
[Apprise setup wiki](https://apprise.readthedocs.io/en/latest/setup/).

## Getting started

1. Open **Settings → Notifications → Apprise notifications**.
2. Find the Apprise URL for your service in the Apprise documentation and
   copy it.
3. Click **Add URL**.
4. Paste the URL into the **URL** field. Optionally give it a **Label**, such
   as "Family Slack", so you can tell destinations apart.
5. Make sure **Enable** is switched on, then click **Save**.
6. Choose **Save and test** when asked, or click **Send test** on the saved
   entry, to confirm a test message arrives.
7. Turn on Apprise for the notification types you want (see
   [Enable or disable per type](#enable-or-disable-per-type)).

!!! note
    Apprise URLs usually contain secret tokens. Nexara stores them encrypted
    and never shows them again after saving. To change one, edit the entry and
    paste the new URL. Treat the URL like a password.

## Examples

Replace the placeholder values with your own. Each line can be pasted
directly into the **URL** field.

**Slack** (three tokens from your Slack incoming webhook URL):

```text
slack://TokenA/TokenB/TokenC/#general
```

**Discord** (from the webhook URL `https://discord.com/api/webhooks/ID/TOKEN`):

```text
discord://webhook_id/webhook_token
```

**Telegram** (bot token from @BotFather and your chat ID):

```text
tgram://bot_token/chat_id
```

**Email** (the server must be able to send mail, for example via SMTP
credentials in the URL):

```text
mailto://user:app-password@example.com
```

**SMS through AWS SNS** (access key, secret, region, and a phone number in
international format):

```text
sns://AccessKeyID/AccessKeySecret/us-east-1/+15551234567
```

## Troubleshooting

**The test fails or shows "Test failed".**
Check that the service is reachable from the server running Nexara. A
self-hosted instance behind a restrictive firewall may need outbound access
to the service. Confirm that the token or webhook has not been revoked.

**"Invalid Apprise URL" appears when saving.**
The URL does not match the format Apprise expects for that service. Compare
it character by character with the example in the Apprise documentation.
Common mistakes are a missing scheme (`slack://`), extra spaces, and
unencoded special characters in passwords. Percent-encode characters such
as `@`, `:` and `/` inside credentials.

**Messages arrive late or only some are delivered.**
Services enforce rate limits. If many notifications fire in a short time, the
service may reject or delay some of them. Reduce the number of enabled
notification types for that destination, or use a quieter channel.

**Nothing arrives, but the test works.**
Apprise may be disabled for that notification type. Check the matrix in
**Settings → Notifications**, and make sure the URL itself is enabled.

## Enable or disable per type

Each notification type, such as event reminders or new comments, has its own
row in the notification matrix under **Settings → Notifications**. The
**Apprise** column controls whether that type is also sent to your Apprise
URLs. Switch it on for the types you care about and off for the rest. The
in-app, push, and email columns are independent, so you can, for example,
send urgent items to Apprise only.

To pause one destination without deleting it, switch off **Enable** on its
entry. To remove it permanently, use **Delete**; this cannot be undone.
