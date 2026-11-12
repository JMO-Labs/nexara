# Sassybot

Sassybot is an optional, playful AI commenter. It occasionally replies to posts with a short
(under 200 characters) witty comment. It looks at attached images too. It is meant to be
fun, never mean.

## When Sassybot comments

- By default it comments on about **15%** of new posts.
- Mention **@sassybot** in a post or comment to summon it every time.
- It never posts more than **3 comments** on one post.
- If the AI provider is not configured or its budget is used up, Sassybot stays quiet.

## Sass levels

| Level | Tone |
| ----- | ---- |
| 1 | Mild: gentle teasing |
| 2 | Moderate (default) |
| 3 | Spicy: bolder, still kind |

## Opting out

Open **Settings** and turn on the Sassybot opt-out. Sassybot will no longer comment on your
posts, including when someone mentions it on them.

## Admin settings

| Setting | Default | Meaning |
| ------- | ------- | ------- |
| `sassybot_enabled` | true | Turn Sassybot on or off for the community |
| `sassybot_sass_level` | 2 | 1 mild, 2 moderate, 3 spicy |
| `sassybot_probability` | 15 | Percent chance of commenting on a new post (0-100) |
| `sassybot_invoke_only` | false | Only comment when @mentioned |

Set `SASSYBOT_USER_ID` to the id of the bot user account whose name appears on its comments,
and configure `AI_PROVIDER`.
