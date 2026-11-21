# Polish Patterns: Where They Fit

Date: 2026-11-19. These are references, not dependencies. All four are Framer-only marketplace
components (no npm package), so we rebuild the interaction with framer-motion and our own tokens
(glass, `--nx-*`, Outfit). Not part of the home glass bento plan; each is a follow-up ticket.

| Reference | What it does | Best fit in Nexara | Also good for |
|---|---|---|---|
| [Expand Image Cards](https://www.framer.com/marketplace/components/expand-image-cards/) | Row of image cards. Selecting one widens it to show details and a link. Turns into a vertical accordion on phones. | **Galleries index** (`/app/galleries`): each album is a tall cover card that expands to show title, photo count, latest contributors, and "Open album". | **Groups directory** (`/app/subgroups`): cover image, description, member avatars, Join. The phone accordion matches the home tiles. |
| [Modern Timeline](https://www.framer.com/marketplace/components/modern-timeline/) | Curved, wavy timeline with up to 30 milestones. Glowing markers; navigate by drag, wheel, keys or click. | **Group or family story**: a "Traditions" or "Our story" tab on a group page, built from tradition prompts, kudos and milestone events. | **Event day-of agenda** (multi-part events like a reunion weekend). **Onboarding**: show progress through setup steps. |
| [Meridian](https://www.framer.com/marketplace/components/meridian/) | Minimal year ruler under a fixed needle. The year rolls into place and each year's photo and story fade in. | **Year in review / memories**: browse a group's photos and posts by year, ending with an "On this day" card. | **Photo archive** navigation by year inside a large gallery. **Member profile**: a personal timeline (joined, birthdays, milestones). |
| [Get in Touch](https://www.framer.com/marketplace/components/get-in-touch/) | Contact section: heading, details and form; reveals on scroll; success state; boxed, underline or filled inputs. | **Public landing page**: "Request an invite" form when `REQUIRE_INVITE=true`, sent to admins as a notification (no third-party form service). | **Help → Contact the admins**, the **moderation report** dialog, and the **first-admin setup** screen. Its input styles can become the shared form treatment for settings. |

**[Dynamic Island Nav](https://www.framer.com/marketplace/components/dynamic-island-nav/)**: a floating nav where a spring-driven pill glides between links and the bar folds into the current item on scroll down. **Already in the home plan (Task 7)**: the desktop top pill nav glides and compacts on scroll. The phone tab bar gets the gliding pill but stays pinned.

## Rules when building these
- Reduced motion: static layout and instant transitions.
- Keyboard: every expand, timeline step, or year is a button with visible focus; arrow keys move between items.
- Data comes from existing APIs (galleries, subgroups, prompts, events); no new content types for the visuals alone.
- No third-party form backends: forms post to our API, which notifies admins in-app and by email.
