# 🛰 Radar — Telegram bot MVP

**Radar** is a personal information filter. A user chooses interests, the bot collects fresh material from open RSS feeds, filters it by topic, remembers what was already shown and sends a compact selection.

## What is included

- polished onboarding with a generated welcome banner;
- preset interests;
- free plan: 5 interests / 5 items per digest;
- Premium: 20 interests / 12 items per digest;
- Telegram Stars subscription: 199 ⭐ / 30 days;
- 👍 / 👎 feedback;
- daily digest with configurable hour;
- PostgreSQL persistence;
- Telegram webhook via FastAPI;
- Render deployment;
- GitHub Actions hourly refresh;
- no paid AI API required for the MVP.

## Important architecture choice

The bot does **not** depend on your computer being on. Telegram sends updates to the deployed Render service through HTTPS, while GitHub Actions periodically calls the refresh endpoint. PostgreSQL stores users, interests and delivery history.

The free hosting providers' limits and availability can change, so treat this as an MVP deployment rather than a guarantee of unlimited free production hosting.

## Deploy without keeping your PC on

### 1. Create the bot

In Telegram open **@BotFather**, create a bot and copy its token.

### 2. Create PostgreSQL

Create a free PostgreSQL project (for example, Supabase's free tier) and copy its connection string.

### 3. Put this folder in GitHub

Create a private or public repository and upload the project contents.

### 4. Deploy on Render

Create a Web Service from the repository. `render.yaml` contains the basic service definition.

Set:

- `BOT_TOKEN` — token from BotFather;
- `DATABASE_URL` — PostgreSQL connection string;
- `WEBHOOK_BASE_URL` — your Render HTTPS URL, for example `https://radar-bot.onrender.com`;
- `WEBHOOK_SECRET` — long random string;
- `CRON_SECRET` — another long random string.

After deployment, opening `/health` should return `{"status":"healthy"}`.

### 5. Configure GitHub Actions

In GitHub repository → Settings → Secrets and variables → Actions add:

- `RADAR_URL` = your Render HTTPS URL;
- `CRON_SECRET` = exactly the same value as Render.

The workflow runs every hour and checks each user's local configured digest hour.

## Local development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

For local Telegram testing you need a public HTTPS endpoint for the webhook. For local-only development, polling can be added later, but production uses webhook mode.

## Premium

Digital goods/services sold inside Telegram use Telegram Stars (`XTR`). The project creates a 30-day recurring Stars invoice. Telegram's current Bot API requires a 30-day subscription period for recurring bot subscriptions. See Telegram's official payment documentation before launch because payment rules and limits can change.

## Current MVP limitations

The first version intentionally uses deterministic topic classification instead of a paid LLM. This keeps the launch cost at zero, but it also means the recommendation quality is not yet as smart as a mature personalized system.

The next upgrades I would make after real user feedback:

1. more high-quality RSS sources per topic;
2. source quality scoring;
3. stronger duplicate detection;
4. per-user interest weights from feedback;
5. custom interests;
6. Mini App with a beautiful feed;
7. analytics and admin dashboard;
8. optional AI reranking after the product proves demand.
