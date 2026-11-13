# Tradition Prompts

## What prompts are

Tradition prompts are recurring posts that invite members to share
something: "Share your favourite holiday photo", "What did you do this
weekend?". When a prompt fires, Nexara creates a pinned post in the feed.
Members reply to it, and when the prompt's window closes Nexara can publish
a summary post.

At most 3 prompt posts are pinned at once per community. If the limit is
reached, further prompts that are due are skipped for that day.

## For admins

Manage prompts in **Admin > Prompts**. Built-in prompts can be disabled but
not deleted. Custom prompts can be created, edited, and deleted.

### Creating a prompt

| Field                | Description                                                        |
| -------------------- | ------------------------------------------------------------------ |
| `title`, `body`      | Shown in the pinned post (title in bold, then body).               |
| `frequency_type`     | Schedule type, see below.                                          |
| `active_days`        | How long the post stays pinned (1-365, default 7).                 |
| `scope`              | `community` or `subgroup` (subgroup requires `subgroup_id`).       |
| `notify_members`     | Send a notification when the prompt fires (default on).            |
| `notification_body`  | Optional custom notification text; defaults to the title.          |
| `generate_summary`   | Publish a summary post when the window ends (default on).          |
| `linked_event_id`    | Optional event to link the prompt to.                              |
| `prompt_type`        | `standard` or `interest_capture` (needs `interest_category_slug`). |

### Scheduling

| `frequency_type` | Trigger fields                                                |
| ---------------- | ------------------------------------------------------------- |
| `annual_date`    | `trigger_month`, `trigger_day`                                |
| `weekly`         | `trigger_weekday` (0 = Monday ... 6 = Sunday)                 |
| `monthly`        | `trigger_month_day`                                           |
| `one_time`       | `trigger_one_time_date`                                       |
| `custom`         | `trigger_custom_rule` (an iCalendar RRULE string)             |

A scheduled job checks for due prompts every day at 06:00 UTC. Each prompt
fires at most once per day. Set `is_enabled` to `false` to pause a prompt.

## For members

Active prompts appear pinned in the feed. Reply with the prompt's reply
action; text and photos are supported. Replies are normal posts linked to
the prompt post.

### Responses page

Each prompt card links to `/app/prompts/<prompt_post_id>`, which lists every
reply to that prompt, newest first, with the prompt title as the heading.

## Summary posts

A daily job at 07:00 UTC finalises prompts whose window has ended. For each
one, Nexara unpins the original post and, if `generate_summary` is on,
publishes a regular summary post with the response count. Photos and other
media from replies are attached in response order, de-duplicated, up to 10
items. The prompt's author is notified. For subgroup prompts the summary is
visible only to that subgroup.

## API endpoints

All endpoints are under `/api/v1/prompts` and require authentication.
Errors use the standard error envelope.

| Method   | Path                                 | Access | Description                                      |
| -------- | ------------------------------------ | ------ | ------------------------------------------------ |
| `GET`    | `/prompts`                           | admin  | List all prompts.                                |
| `POST`   | `/prompts`                           | admin  | Create a custom prompt (201).                    |
| `GET`    | `/prompts/{prompt_id}`               | admin  | Get one prompt.                                  |
| `PATCH`  | `/prompts/{prompt_id}`               | admin  | Update a prompt (all fields optional).           |
| `DELETE` | `/prompts/{prompt_id}`               | admin  | Delete a custom prompt (built-ins are refused).  |
| `GET`    | `/prompts/active`                    | member | List currently pinned prompt posts.              |
| `GET`    | `/prompts/posts/{prompt_post_id}`    | member | Get one fired prompt post with prompt details.   |
| `GET`    | `/prompts/posts/{prompt_post_id}/responses` | member | List replies, newest first. Query: `limit` (1-50, default 20), `cursor`. |

See also [Prompts (user guide)](user/prompts.md).
