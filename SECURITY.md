# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in any DOME repository, please report it
responsibly by emailing **security@domelayer.com**. Do not open a public issue.

We will acknowledge receipt within 48 hours and provide an initial assessment
within 5 business days.

## Secrets Inventory

This service uses the following secret-class environment variables. None are
committed to the repository; they are set exclusively in Railway / Vercel
environment variables and in `.env.local` files (gitignored).

| Variable | Class | Rotation cadence |
|---|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | Service role (full DB access) | On compromise or annual |
| `SUPABASE_ANON_KEY` | Public anon key | Rotated with service role |
| `REDIS_URL` | Connection string (contains password) | On compromise |
| `SENTRY_DSN` | Ingest URL (low sensitivity) | On compromise |

## Rotation Policy

Keys are rotated immediately on suspected compromise and verified by confirming
the old value returns an authentication error. Rotation dates are tracked
internally and are not published in this file.

## `.env` Hygiene

- `.env*` patterns are gitignored (see `.gitignore`).
- Only `.env.example` (with placeholder values) is committed.
- `gitleaks` runs in CI on every push and PR to catch accidental commits.
