## Parent PRD

`issues/prd.md`

## What to build

Provision an Oracle Cloud Free Tier ARM VM, deploy the bot, and configure cron to run it every Saturday and Sunday at 7:58pm (Europe/London). This is a HITL slice — it requires manual Oracle Cloud account setup, SSH access, and cron configuration.

## Acceptance criteria

- [ ] Oracle Cloud Free Tier ARM VM provisioned (Ubuntu, 1GB RAM minimum)
- [ ] Python 3.11+ installed on the VM
- [ ] Bot repository cloned onto the VM
- [ ] `.env` file populated with real credentials on the VM (not committed to git)
- [ ] Playwright and Chromium installed (`playwright install chromium` + system dependencies)
- [ ] `pytest` passes on the VM
- [ ] Server timezone set to `Europe/London`
- [ ] Two cron entries configured:
  - [ ] Saturday 7:58pm: `58 19 * * 6 /path/to/venv/bin/python -m bot.scheduler`
  - [ ] Sunday 7:58pm: `58 19 * * 0 /path/to/venv/bin/python -m bot.scheduler`
- [ ] Cron output redirected to a log file for debugging
- [ ] Manually verified: bot runs on the VM and successfully sends a WhatsApp notification

## Blocked by

- Blocked by `issues/012-scheduler-implementation.md`

## User stories addressed

- User story 18, 19, 20
