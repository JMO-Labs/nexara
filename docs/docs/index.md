# Nexara

> An open-source, self-hosted space for the small community, group, or family.

Nexara is a modern, fast, and attractive platform for small communities
(families, clubs, groups) to share events, photos, messages, and more.
Self-hosted first, container-native, and scaleable to Kubernetes.

## Features

- **Activity Feed** -- Posts with Markdown, GIFs, threaded comments, and reactions
- **Media Sharing** -- Photo and video upload with web-optimized transcoding
- **Calendar and Events** -- FullCalendar UI, recurring events, RSVP, iCal export
- **Real-time Chat** -- WebSocket-based group and direct messaging
- **Subgroups** -- Scoped feeds, events, and chat channels
- **Galleries** -- Named albums with bulk upload and access controls
- **Polls** -- Single, multiple-choice, yes/no, and photo polls with live results
- **Search** -- Full-text search across all content via PostgreSQL FTS
- **Notifications** -- In-app (SSE), push (Web Push), and email
- **Admin Panel** -- User management, community settings, audit log, WAF controls
- **PWA** -- Installable progressive web app with offline shell
- **Plugin System** -- Extensible via backend hooks and frontend slots (Phase 4)

## Tech Stack

| Layer          | Technology                                  |
| -------------- | ------------------------------------------- |
| Frontend       | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui (Radix), TanStack Query, zustand |
| Backend        | FastAPI (async), SQLAlchemy 2.0 async, Celery |
| Database       | PostgreSQL 16                                |
| Cache/Pub-Sub  | Valkey (Redis-compatible)                    |
| Container      | Alpine-based Docker, two containers max      |

## Quick Links

- [Getting Started](getting-started.md) -- Set up a development environment
- [Development Guide](development.md) -- Architecture, conventions, testing
- [Deployment Guide](deployment.md) -- Docker Compose, Helm, unRAID
- [API Reference](api/) -- Doxygen-generated Python backend documentation
- [Backend Coverage](coverage/backend/) -- pytest coverage report
- [Frontend Coverage](coverage/frontend/) -- Vitest coverage report

## License

Nexara is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).
