# Power BI Embedded – Setup Considerations

This document captures the design decisions, security patterns, and future enhancements discussed while building the Contoso Health Analytics Portal.

---

## 1. Multi-Report Access

The app dynamically lists all reports in a Power BI workspace via the REST API (`GET /groups/{workspaceId}/reports`) and displays them in the sidebar and a report picker grid.

### Per-User Report Filtering

Report visibility is controlled **server-side** in `demo_users.json`. Each user has an `allowed_reports` field:

| Value | Behaviour |
|---|---|
| `"*"` | User can see **all** reports in the workspace |
| `["id-1", "id-2"]` | User can only see the listed report IDs |
| `[]` | User sees **no** reports |

Both the `/api/reports` list endpoint and the `/getembedinfo` embed token endpoint enforce this filter. A user can never obtain an embed token for a report outside their allowed set.

---

## 2. Row-Level Security (RLS)

RLS restricts which **rows of data** a user can see within a report. It is defined in the Power BI data model (Power BI Desktop → Modeling → Manage Roles) and enforced by passing an `EffectiveIdentity` in the `POST /GenerateToken` request.

### Prerequisites

- The `.pbix` file **must** have one or more RLS roles defined with DAX filter expressions.
- The report must be republished to the Power BI service after adding/removing roles.

### How It Works

When generating an embed token, the app includes:

```json
{
  "identities": [{
    "username": "<value>",
    "roles": ["<RoleName>"],
    "datasets": ["<dataset-id>"]
  }]
}
```

| Field | Purpose |
|---|---|
| `username` | For **dynamic RLS** (`USERNAME()` DAX function), this value is used as the filter. For **static RLS**, it can be any string. |
| `roles` | Must match the exact role name(s) defined in Power BI Desktop. |
| `datasets` | The dataset(s) the identity applies to (auto-populated by the app). |

### Key Rules

1. **If the dataset has RLS roles**, you **must** pass an `EffectiveIdentity` — omitting it with a service principal causes a `400 Bad Request`.
2. **If the dataset has no RLS roles**, you **must not** pass an `EffectiveIdentity` — including one causes a `400 Bad Request`.
3. Set `"rls": null` in `demo_users.json` for datasets without RLS.

### Static vs Dynamic RLS

| Type | DAX Example | `username` Value |
|---|---|---|
| **Static** | `[Region] = "East"` | Any string (ignored by DAX) |
| **Dynamic** | `[Region] = USERNAME()` | The value to filter by (e.g., `"East"`) |

> **Reference:** [Microsoft – Embed a report with RLS](https://learn.microsoft.com/en-us/power-bi/developer/embedded/cloud-rls)

### Configuration in `demo_users.json`

```json
"analyst": {
  "password": "analyst",
  "display_name": "Brian Analyst",
  "role_label": "Regional Analyst — East",
  "allowed_reports": "*",
  "rls": {
    "username": "East",
    "roles": ["RegionalAnalyst"]
  }
}
```

Set `"rls": null` for users that should see unfiltered data (only valid when the dataset has no RLS roles).

---

## 3. Multi-Workspace Support (Future Enhancement)

Currently the app uses a single `--workspace-id` CLI argument. To support users accessing reports across multiple workspaces, the following changes are needed:

### Proposed `demo_users.json` Schema

```json
"admin": {
  "password": "admin",
  "display_name": "Alice Administrator",
  "role_label": "System Administrator",
  "workspaces": ["<workspace-A-id>", "<workspace-B-id>"],
  "allowed_reports": "*",
  "rls": null
},
"viewer": {
  "password": "viewer",
  "display_name": "Carla Viewer",
  "role_label": "Clinic Viewer",
  "workspaces": ["<workspace-A-id>"],
  "allowed_reports": ["<specific-report-id>"],
  "rls": null
}
```

### What Changes

| Component | Current | Multi-Workspace |
|---|---|---|
| CLI `--workspace-id` | Required, single ID | Optional fallback default |
| `/api/reports` | Queries 1 workspace | Loops through user's `workspaces`, merges results, tags each report with its `workspaceId` |
| `/getembedinfo` | Uses global workspace ID | Looks up the report's workspace from the cached list |
| `demo_users.json` | No workspace info per user | `workspaces` array per user |
| Sidebar | Flat report list | Optionally grouped by workspace |

### Flow

1. User logs in → app reads their `workspaces` list
2. `/api/reports` queries each workspace, merges results, filters by `allowed_reports`
3. Each report object carries its `workspaceId`
4. When embedding, `/getembedinfo` uses the report's own `workspaceId` for the token request

### Sidebar UX Options

- **Flat list** — all reports together, sorted by name
- **Grouped** — a collapsible section per workspace

---

## 4. Security Summary

| Layer | What It Controls | Where It's Enforced |
|---|---|---|
| **App login** | Who can access the portal | Flask session (Flask-Login) |
| **Report access** | Which reports a user can see/embed | `allowed_reports` in `demo_users.json`, checked server-side |
| **Row-Level Security** | Which rows of data a user sees within a report | `EffectiveIdentity` passed to Power BI `GenerateToken` API |
| **Multi-workspace** *(future)* | Which workspaces a user can browse | `workspaces` array in `demo_users.json`, queried server-side |

All security decisions happen in Python on the server. The JavaScript frontend is "dumb" — it only renders what the backend permits.

---

## 5. References

- [Microsoft – Embed for your customers (App Owns Data)](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-sample-for-customers)
- [Microsoft – Row-Level Security in Power BI Embedded](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embedded-row-level-security)
- [Microsoft – Embed a report with RLS](https://learn.microsoft.com/en-us/power-bi/developer/embedded/cloud-rls)
- [Microsoft – Generate an embed token](https://learn.microsoft.com/en-us/power-bi/developer/embedded/generate-embed-token)
- [Power BI JS SDK Reference](https://learn.microsoft.com/en-us/javascript/api/overview/powerbi/)
