# Oracle Cloud Free Tier Deployment Runbook

This is the HITL procedure for issue 013 — provisioning an Always-Free ARM VM, deploying the bot, and configuring cron. All steps below are to be performed by a human; the bot code itself (issues 001–012) is ready to run.

## 1. Provision the VM

1. Sign in at [cloud.oracle.com](https://cloud.oracle.com/) and open **Compute → Instances → Create instance**.
2. Image: **Canonical Ubuntu 22.04** (or 24.04).
3. Shape: **VM.Standard.A1.Flex** (Always Free). 1 OCPU / 6 GB RAM is fine and still within free-tier caps.
4. Networking: create (or reuse) a VCN with a public subnet, and assign a public IPv4 address.
5. SSH keys: upload your public key.
6. In the VCN's default security list, add an **Ingress** rule for TCP 22 from your IP.

## 2. First-time setup on the VM

```bash
ssh ubuntu@<public-ip>

sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git \
    libnss3 libnspr4 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2

curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

sudo timedatectl set-timezone Europe/London
timedatectl    # verify
```

## 3. Deploy the bot

```bash
git clone git@github.com:<your-user>/tennis-bot2.git
cd tennis-bot2

uv sync
uv run playwright install --with-deps chromium

cp .env.example .env
vi .env   # fill in real LTA, Twilio, court URLs, allowlist

uv run pytest -q   # expect 50 passed
```

## 4. Smoke test

```bash
uv run python -m bot.scheduler
```

This logs into LTA, scans the three courts, and either:
- adds a slot to basket and sends a "slot found" WhatsApp, or
- sends a "nothing available" WhatsApp after ~5 minutes, or
- sends an "error" WhatsApp and exits non-zero.

If you see an error, check `~/tennis-bot2/.state/session.json` and iterate.

## 5. Cron configuration

```bash
crontab -e
```

Add:

```
PATH=/home/ubuntu/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
58 19 * * 6  cd /home/ubuntu/tennis-bot2 && /home/ubuntu/.cargo/bin/uv run python -m bot.scheduler >> /home/ubuntu/tennis-bot2/cron.log 2>&1
58 19 * * 0  cd /home/ubuntu/tennis-bot2 && /home/ubuntu/.cargo/bin/uv run python -m bot.scheduler >> /home/ubuntu/tennis-bot2/cron.log 2>&1
```

Verify the timezone with `crontab -l && date`; cron honours the system timezone set above.

## 6. Verification checklist

- [ ] `pytest` passes on the VM
- [ ] `timedatectl` shows `Europe/London`
- [ ] `crontab -l` lists both entries
- [ ] A manual `uv run python -m bot.scheduler` at any time reaches the "nothing available" WhatsApp (courts aren't open, so this is the expected path outside the 8pm window)
- [ ] Saturday 19:58 local: `cron.log` shows a run starting, and a WhatsApp arrives on +447512211264 within ~6 minutes
