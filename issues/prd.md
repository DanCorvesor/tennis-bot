# PRD: Tennis Court Booking Bot

## Problem Statement

Tennis courts at three Southwark-area parks (Southwark Park, Brunswick Park, Burgess Park) are bookable via ClubSpark. Each week, new slots open at exactly 8pm — 7 days in advance — and are fully booked within minutes. Manually refreshing the booking page at the right moment and being fast enough to secure a preferred slot is unreliable. The user needs an automated solution that can react the instant slots become available, add a court to the basket, and notify them to complete payment immediately.

---

## Solution

A Python bot that runs on a scheduled cron job every Saturday and Sunday evening. Starting before the 8pm release window, it polls the ClubSpark availability pages for three courts. The moment a preferred slot becomes available, it logs in via LTA SSO, adds the slot to the ClubSpark basket, and sends an instant WhatsApp notification (via Twilio) to the user with a direct link to complete payment. If no slots are found after a retry window, it sends a "nothing available" notification. Any errors during execution also trigger a WhatsApp alert.

---

## User Stories

1. As a tennis player, I want the bot to automatically start scanning court availability just before 8pm on Saturdays and Sundays, so that I don't have to be at my computer at the exact release time.
2. As a tennis player, I want the bot to scan all three of my preferred Southwark courts simultaneously, so that I have the best chance of securing any available slot.
3. As a tennis player, I want the bot to prefer 10am slots over 11am and 9am, so that I get my preferred playing time when possible.
4. As a tennis player, I want the bot to prefer Saturday slots over Sunday slots at each time, so that my weekly preference is respected.
5. As a tennis player, I want the bot to book 1-hour slots only, so that the booking matches how I play.
6. As a tennis player, I want the bot to log in to ClubSpark using my LTA credentials automatically, so that I don't need to be logged in manually when the bot runs.
7. As a tennis player, I want the bot to persist my LTA login session between runs, so that it doesn't need to go through the full OAuth flow every week.
8. As a tennis player, I want the bot to add the best available slot to my basket immediately upon finding it, so that the booking process is as fast as possible.
9. As a tennis player, I want the bot to send me a WhatsApp message the moment a slot is added to my basket, so that I can open the link and pay before someone else does.
10. As a tennis player, I want the WhatsApp message to include a direct link to the ClubSpark basket, so that I can complete payment with minimal taps.
11. As a tennis player, I want the WhatsApp message to clearly state which court, day, and time was found, so that I know what I'm about to pay for.
12. As a tennis player, I want the bot to retry for up to 5 minutes after 8pm if no slots are initially found, so that I don't miss last-second cancellations or delayed releases.
13. As a tennis player, I want the bot to send me a WhatsApp notification if no slots were found after the full retry window, so that I know the bot ran and there was genuinely nothing available.
14. As a tennis player, I want the bot to send me a WhatsApp notification if it encounters an error (e.g. login failure, page not loading), so that I can intervene manually if needed.
15. As a tennis player, I want the list of WhatsApp recipients to be configurable as an allowlist, so that I can add friends to the notification group in future.
16. As a tennis player, I want all credentials and configuration stored in a `.env` file, so that sensitive values are never hardcoded.
17. As a tennis player, I want the option to store card details in `.env` as a fallback, so that if the basket link approach proves too slow, the bot can complete payment automatically.
18. As a tennis player, I want the bot to run on a cloud server (Oracle Cloud Free Tier), so that it runs reliably every week without needing my laptop to be on.
19. As a tennis player, I want the cron schedule to trigger the bot on both Saturday and Sunday evenings, so that I can capture weekend slots on either day.
20. As a tennis player, I want the bot to poll at increasing frequency as 8pm approaches (every 5s from 7:58pm, every 1s in the final 30 seconds), so that it reacts as close to the release moment as possible.

---

## Implementation Decisions

### Modules

**1. Config Loader**
Reads all settings from `.env` into a typed configuration object. Provides a single source of truth for credentials, court URLs, time preferences, Twilio settings, and the WhatsApp allowlist. All other modules consume config through this interface.

**2. Session Manager**
Handles LTA SSO authentication using Playwright. On first run, performs the full OAuth login flow (LTA login page → redirect back to ClubSpark). Persists browser cookies/storage to disk so subsequent runs reuse the session without re-authenticating. Detects expired sessions and re-authenticates automatically.

**3. Court Scanner**
Given a list of court URLs and a priority-ordered list of (day, time) tuples, polls the ClubSpark availability pages to find the first available slot matching the preferences. Runs against all three courts. Returns the first matching (court, day, time, booking URL) tuple, or nothing if unavailable.

**4. Basket Manager**
Given a booking URL for a specific slot, uses the authenticated Playwright session to navigate to the slot and add it to the basket. Returns the ClubSpark basket URL upon success.

**5. Notifier**
Sends WhatsApp messages via the Twilio API to all numbers in the allowlist. Supports three message types: slot found (with basket URL), nothing available, and error (with description). Stateless — takes message content and recipient list as inputs.

**6. Scheduler / Entry Point**
The main script invoked by cron. Orchestrates the full flow:
- Start polling at 7:58pm
- Ramp up polling frequency as 8pm approaches
- On slot found: invoke Basket Manager → Notifier (found)
- On 5-min timeout with nothing found: Notifier (nothing available)
- On any exception: Notifier (error)

### Technical Decisions

- **Browser automation**: Playwright (Python async) in headless mode.
- **LTA SSO**: Full OAuth redirect flow automated via Playwright. No 2FA on the account, so standard form fill is sufficient.
- **Session persistence**: Playwright browser context stored to disk (cookies + localStorage). Reloaded at the start of each run.
- **Polling strategy**: 5-second intervals from 7:58pm → 1-second intervals from 7:59:30 → 10-second intervals from 8:00pm for up to 5 minutes.
- **Slot priority order**: Sat 10am, Sun 10am, Sat 11am, Sun 11am, Sat 9am, Sun 9am — checked across all three courts at each priority level.
- **Basket link approach**: Bot adds slot to basket; user pays manually via the link. No card details required unless this fails in practice.
- **Card fallback**: Card number, expiry, CVV, and name can be added to `.env` (commented out by default). If enabled, the bot completes payment automatically via Playwright form fill.
- **WhatsApp**: Twilio WhatsApp sandbox (or approved number). Sender is the Twilio WhatsApp number; recipients are the allowlist from `.env`.
- **Hosting**: Oracle Cloud Free Tier ARM VM. Bot runs as a cron job (`crontab`). No web server required (no webhook/reply flow in v1).
- **Scheduling**: Two cron entries — one for Saturday 7:58pm, one for Sunday 7:58pm (server timezone set to Europe/London).
- **Credentials**: `.env` file, never committed (`.gitignore` in place).

### `.env` Contract

```
LTA_USERNAME
LTA_PASSWORD
CLUBSPARK_EMAIL
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_FROM
TWILIO_WHATSAPP_TO          # primary recipient
WHATSAPP_ALLOWLIST          # comma-separated list of numbers
COURTS                      # comma-separated ClubSpark URLs
PREFERRED_TIMES             # comma-separated, e.g. 10:00,11:00,09:00
BOOKING_DAYS                # Saturday,Sunday
SLOT_DURATION_HOURS         # 1
# CARD_NUMBER               # fallback only
# CARD_EXPIRY               # fallback only
# CARD_CVV                  # fallback only
# CARD_NAME                 # fallback only
```

---

## Testing Decisions

**What makes a good test**: Tests should validate observable external behaviour — what the module returns or what side effects it produces — not how it achieves it internally. For example, test that the Notifier calls the Twilio API with the correct payload, not that it instantiated a specific internal object.

**Modules to test**:

- **Config Loader**: Test that all required fields are loaded correctly, that missing required fields raise a clear error, and that optional fields have correct defaults.
- **Court Scanner**: Test the priority ordering logic — given a mocked availability response, assert the scanner returns the highest-priority available slot. Test that it correctly skips unavailable slots. Mock the HTTP/Playwright layer.
- **Notifier**: Test that the correct Twilio API call is made for each message type (found, nothing available, error). Mock the Twilio client. Test that all numbers in the allowlist receive the message.
- **Scheduler (entry point)**: Integration-style test with mocked Scanner and Notifier — assert the correct message type is sent given different scanner outcomes (found, not found, exception).

**Basket Manager and Session Manager** are tightly coupled to the browser and ClubSpark's live HTML — these are best validated manually against the live site rather than with automated tests, to avoid brittle DOM-selector assertions.

---

## Out of Scope

- Booking multiple courts in a single run (only one court per execution).
- A reply-to-confirm WhatsApp flow (dropped in favour of instant basket notification).
- A web dashboard or admin UI.
- Handling 2FA on the LTA account.
- Support for booking platforms other than ClubSpark.
- Rescheduling or cancelling existing bookings.
- Tracking historical bookings or availability patterns.
- Group-chat-based confirmation (any member triggering a booking).
- Automatic payment completion (out of scope unless basket link approach fails).

---

## Further Notes

- The basket does **not** hold the slot — another user can book the same slot while the user is navigating to pay. Speed between the bot adding to basket and the user completing payment is critical.
- If the basket link approach consistently results in losing slots, the card details fallback should be enabled and the Basket Manager extended to complete the Playwright checkout flow automatically.
- The LTA session cookie should be monitored for expiry. If the bot detects it is logged out mid-run, it should re-authenticate and retry once before sending an error notification.
- Oracle Cloud ARM VMs run Ubuntu. The bot will need Playwright's Chromium browser installed (`playwright install chromium`) and a systemd-managed Python environment.
- Server timezone must be set to `Europe/London` to ensure cron fires at the correct local time, accounting for GMT/BST transitions.
