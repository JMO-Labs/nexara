# FAQ

## Community setup

**How do I create my community?**
The first account created on a fresh instance becomes the administrator. Use
the admin panel to name the community, set the logo, and invite members.

**Can I run more than one community?**
Data is scoped by community internally, but the standard install is designed
for a single community per instance. Run a second instance for a separate group.

**How do members join?**
Administrators send email invitations. Registration can be limited to invited
users only.

## Privacy

**Who can see my posts?**
That depends on the visibility you choose: the whole community, a single
subgroup, or only you. Private items are never shown to other members, and
administrators see them only through direct database access.

**Does Nexara send data to third parties?**
No analytics or tracking services are included. Outbound traffic is limited to
what you configure, such as your SMTP server and browser push services.

**Can I block someone?**
Yes. Blocked users are hidden from your feeds and comments.

## Permissions

**What roles exist?**
Members and administrators. Administrators manage users, community settings,
and moderation, and can review the audit log.

**Who can create subgroups?**
Administrators create subgroups and assign members to them.

## Backups

**What should I back up?**
The PostgreSQL database and the media volume. See [Self-Hosting](self-hosting.md#backups).

**How do I restore?**
Restore the database dump, restore the media files to the same volume path,
and start the stack. Migrations bring the schema up to date on boot.

**Can I move to another server?**
Yes. Back up, copy both parts, and keep the same `SECRET_KEY` so existing
sessions and tokens remain valid.
