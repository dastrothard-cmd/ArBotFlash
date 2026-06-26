# Administration and review workspace

## Location

Run ArbotFlash locally, then open:

```text
http://127.0.0.1:8080/admin/
```

The workspace shows:

- Total taxa
- Source-enriched taxa
- Licensed media count
- Review-decision count
- Current source warning
- Reconciliation records by source and status
- Proposed identifier, name, rank and confidence
- Evidence notes and previous decision count

## Safe default

The review workspace is read-only unless the server process has an administrator token:

```bash
ARBOTFLASH_ADMIN_TOKEN="choose-a-long-local-token" python -m apps.api.main
```

Enter the same value in the browser workspace. The browser sends it only in the `X-ArbotFlash-Admin-Token` request header. The project does not contain a default token.

This is a development safeguard, not the final public authentication system. Production will use proper user accounts, roles, server-side sessions and row-level policies.

## Decisions

The development API permits three decisions:

- `approve` — accept the proposed external match as reviewed evidence
- `reject` — record that the proposed match is not acceptable
- `defer` — keep the item unresolved pending better evidence

A decision:

1. Updates the queue status.
2. Inserts a `review_decision` row.
3. Inserts an `audit_event` containing before and after state.
4. Rebuilds the read projection.
5. Adds the proposed external identifier on approval when one exists.

It does not delete the original study name or silently rewrite the canonical taxon.

## API endpoints

```text
GET  /api/admin/overview
GET  /api/admin/reconciliation
POST /api/admin/reconciliation/{taxon_id}/{source_key}/decision
```

Optional queue parameters:

```text
status=pending
source=catalogue_of_life
limit=250
```

Decision body:

```json
{
  "decision": "approve",
  "rationale": "Candidate name, rank and classification agree with the reviewed authority record.",
  "reviewer": "Reviewer name"
}
```

## Production requirements

Before public moderation is enabled:

- Replace the shared development token with authenticated accounts.
- Add reviewer roles and permissions.
- Protect personally identifying reviewer data.
- Add second-review requirements for destructive or high-impact changes.
- Make audit records append-only.
- Add rollback tooling.
- Add conflict-resolution screens rather than reducing disagreement to a single button.
