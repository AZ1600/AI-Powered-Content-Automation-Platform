# One Piece X Content Automation Platform

A low-cost serverless control center for two One Piece X accounts:

- `account1`: manga-first reactions, theories, and clearly labelled spoilers.
- `account2`: anime-safe episode, trailer, movie, and adaptation discussion.

The platform stores plans, queues approved posts at Europe/London posting times, publishes through X OAuth, and exposes a browser dashboard for review and manual control.

## What It Does

- OAuth 2.0 PKCE connection flow for two X accounts.
- Private token storage in AWS Secrets Manager.
- Daily plan storage, review, and queueing.
- Ten timezone-aware AWS Scheduler posting windows per day.
- Live dashboard for account health, plans, queue, publishing activity, and manual drafts.
- Protected write endpoints using an automation API key.
- **World Radar**: sourced official news and clearly labelled fan-conversation signals stored with each plan.
- Secure image attachments: JPEG, PNG, and WebP up to 5 MB, stored privately in S3 and attached to X at publish time.

## Architecture

```text
Codex daily automation
  -> sourced plan JSON + World Radar
  -> bridge client
  -> API Gateway + Lambda
  -> DynamoDB plans / queue / activity
  -> AWS Scheduler
  -> X API publishing

Dashboard browser
  -> API Gateway
  -> private S3 image upload URL
  -> queued X post with media attachment
```

The stack uses API Gateway HTTP API, Lambda, DynamoDB on-demand, EventBridge Scheduler, Secrets Manager, and a private S3 media bucket. It does not require a server, database instance, NAT Gateway, or provisioned concurrency.

## Repository Layout

```text
├── automation/
│   ├── one_piece_x_platform_client.py
│   └── one-piece-x-growth.automation.toml.example
├── lambdas/
│   ├── dashboard.html
│   ├── x_dashboard.py
│   ├── x_media_presign.py
│   ├── x_publisher.py
│   └── ...
├── templates/template.yaml
├── tests/test_x_platform.py
└── samconfig.toml
```

## Deploy To A New AWS Account

Prerequisites:

- AWS CLI profile with deployment permissions.
- AWS SAM CLI.
- An approved X developer app with OAuth 2.0 enabled.

Initial deployment:

```bash
sam build -t templates/template.yaml
sam deploy --guided --profile YOUR_AWS_PROFILE --region eu-west-2
```

After the first deploy:

1. Copy the `XApiBaseUrl` CloudFormation output.
2. In the X developer portal, register `<XApiBaseUrl>/oauth/x/callback` as the callback URL.
3. Store the X OAuth client secret in `<stack-name>/social/x/client-secret` in Secrets Manager.
4. Deploy again with `OAuthCallbackBaseUrl` set to `XApiBaseUrl`.
5. Connect both accounts using `/oauth/x/start?account_id=account1` and `/oauth/x/start?account_id=account2`.

Never commit AWS credentials, X tokens, client secrets, or the automation API key.

## Dashboard

Open:

```text
https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/dashboard
```

The dashboard shows account totals, saved plans, World Radar sources, queued posts, and activity. It accepts the automation API key only in browser memory for protected actions. The key is not stored in local storage or embedded in the page.

## Daily Growth Automation

The automation writes a dated Markdown plan and a JSON plan, then calls the bridge:

```bash
export ONE_PIECE_X_PLATFORM_BASE_URL="https://YOUR_API_ID.execute-api.eu-west-2.amazonaws.com"
export ONE_PIECE_X_PLATFORM_API_KEY="$(aws secretsmanager get-secret-value \
  --secret-id YOUR_STACK/automation/api-key \
  --profile YOUR_AWS_PROFILE \
  --region eu-west-2 \
  --query SecretString --output text)"

python3 automation/one_piece_x_platform_client.py --plan-file /absolute/path/to/daily-plan.json
```

The plan JSON may include a top-level `world_radar` list. Each item requires:

```json
{
  "title": "Official announcement title",
  "category": "official_news",
  "why_now": "Why this matters for today's conversation",
  "source_url": "https://official-source.example",
  "account_relevance": "account2"
}
```

Use direct official sources where possible. Fan trends must be labelled as fan signals, not news. The automation should recommend a small number of thoughtful engagement opportunities but must not auto-reply or mass-engage.

## Images

In **Manual draft**, choose an original or licensed JPEG, PNG, or WebP image up to 5 MB. The browser uploads it directly through a five-minute signed URL to the private S3 bucket. At publish time, Lambda uploads the image to X and attaches the returned media ID to the post.

Do not automatically download or repost anime episodes, film footage, trailers, or artwork without rights to use them.

## Key Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /dashboard` | Grand Line Control dashboard |
| `GET /x/summary` | Account totals |
| `GET /x/plans?account_id=account1` | Saved plans and World Radar |
| `GET /x/queue?account_id=account1` | Queued posts |
| `GET /x/activity?account_id=account1` | Published, failed, and removed posts |
| `POST /x/plan` | Save a plan |
| `POST /x/plan/queue` | Queue a plan |
| `POST /x/post` | Queue or publish a manual post |
| `POST /x/media/presign` | Create a private image upload URL |
| `POST /x/queue/publish` | Publish an approved queued post |
| `POST /x/queue/remove` | Remove a queued post |

All write endpoints require an `X-Automation-Key` request header.

### Explicit publishing approval

`POST /x/post` accepts optional `queue_only` and `approved` flags, and
`POST /x/queue/publish` accepts an optional `approved` flag. If supplied,
these must be **JSON booleans** (`true` or `false`), not strings or numbers.
Missing approval is treated as `false`; attempting to publish without explicit
`approved: true` is rejected. Invalid flag types return HTTP 400 without
calling the publishing operation. The scheduler only treats stored
`auto_approved` as approved when its value is the Boolean `true` and the
publish mode is `scheduled`.

This is input validation, not a replacement for the required automation API key
or for careful review of scheduled content. No live X publishing is performed
by the regression tests.

## Cost Controls

- DynamoDB uses on-demand billing and TTL: plans expire after 90 days; post history expires after 180 days.
- Uploaded media expires after 30 days.
- Scheduler runs only at the ten planned daily time slots.
- Lambda uses 256 MB memory and a 30-second timeout.
- Avoid provisioned concurrency, NAT Gateway, RDS, and always-on compute for this workload.

## Verify

```bash
sam validate --template-file templates/template.yaml
sam build -t templates/template.yaml
python3 -m pytest -q
```

`pytest` is optional in environments where it is not installed.
