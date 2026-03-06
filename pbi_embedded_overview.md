# Power BI Embedded — Setup Guide for BI Professionals

> This guide explains how Power BI Embedded works and what you need to set up. It's written for people who know Power BI but may be new to embedding reports in custom applications.

---

## What Is Power BI Embedded?

Normally, users view reports in the Power BI Service (app.powerbi.com). With **Power BI Embedded**, you take those same reports and display them inside your own web application. The end user never visits Power BI directly — they see the report inside your app, fully interactive, with slicers, filters, drill-through, and page navigation all working.

**Key benefit:** Your end users do **not** need Power BI Pro or Premium Per User licenses.

---

## Two Embedding Patterns

| Pattern | Who logs in to Power BI? | License needed per user? | Best for |
|---|---|---|---|
| **App Owns Data** (embed for your customers) | Your app (service principal or master account) | No | External users, customer portals, ISV apps |
| **User Owns Data** (embed for your organisation) | Each individual user via Azure AD | Yes (Pro/PPU) | Internal dashboards where users already have licenses |

This guide focuses on **App Owns Data** — the most common pattern for customer-facing scenarios.

---

## What You Need

### Power BI Side (the BI work you already know)

1. **A Power BI workspace** — this is where your reports and datasets live, just like normal
2. **Published reports** — develop in Power BI Desktop, publish to the workspace as usual
3. **Row-Level Security (optional)** — if different users should see different data, define RLS roles in Power BI Desktop using DAX filters, then publish

### Azure Side (one-time setup, usually done by IT/admin)

4. **Microsoft Entra ID (Azure AD) app registration** — this gives your web app a "Client ID" and "Client Secret" that authenticate it with Power BI's API
5. **Service principal access** — the app registration must be added as a Member of your Power BI workspace, and a tenant admin must enable "Service principals can use Fabric APIs" in the Power BI Admin Portal

### Application Side (the web app)

6. **A web server** — any language/framework (Python, .NET, Node.js, etc.) that can make REST API calls
7. **Power BI JavaScript SDK** — a client-side library that renders the report in the browser

---

## How It Works — Step by Step

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE FULL FLOW                                │
│                                                                     │
│   YOU (BI Pro)          YOUR WEB APP              POWER BI API      │
│   ─────────────         ──────────────            ──────────────    │
│                                                                     │
│   1. Build report                                                   │
│      in PBI Desktop                                                 │
│          │                                                          │
│   2. Publish to                                                     │
│      workspace                                                      │
│          │                                                          │
│   3. Note the IDs ─────► Stored in app config                      │
│      (workspace,          (Tenant ID, Client ID,                    │
│       report)              Client Secret, etc.)                     │
│                                │                                    │
│                         4. User visits ──► App login page           │
│                                │                                    │
│                         5. App authenticates ──► Azure AD           │
│                            with Client ID/        returns           │
│                            Client Secret          Access Token      │
│                                │                                    │
│                         6. App calls ──────────► GET report info    │
│                            Power BI API           (embed URL,       │
│                                │                   dataset ID)      │
│                                │                                    │
│                         7. App calls ──────────► POST GenerateToken │
│                            Power BI API           (scoped to this   │
│                                │                   report + RLS)    │
│                                │                                    │
│                         8. App sends embed ──► Browser runs         │
│                            token + URL to      Power BI JS SDK,     │
│                            the browser         renders report       │
│                                                 in an iframe        │
│                                                                     │
│                         9. User interacts with the report           │
│                            (slicers, filters, drill-through)        │
│                            — all handled by Power BI's viewer       │
└─────────────────────────────────────────────────────────────────────┘
```

### In plain English:

| Step | What happens | Who does it |
|---|---|---|
| **1–2** | Build and publish reports to a Power BI workspace | You (BI developer), same as always |
| **3** | Copy the Workspace ID and Report ID from the Power BI Service URL | You (one-time config) |
| **4** | A user visits your web app and logs in | End user |
| **5** | Your app authenticates with Azure AD using the registered Client ID and Client Secret | App (automatic, server-side) |
| **6** | Your app calls the Power BI REST API to get the report's embed URL | App (automatic, server-side) |
| **7** | Your app requests a short-lived **embed token** scoped to that specific report | App (automatic, server-side) |
| **8** | The embed token and URL are sent to the browser, and the Power BI JS SDK renders the report | Browser (automatic) |
| **9** | The user interacts with the live report — all interactivity works because it's Power BI's own viewer running inside an iframe | End user |

---

## Where Do the IDs Come From?

Open your report in the Power BI Service. The URL looks like:

```
https://app.powerbi.com/groups/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/reports/YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY
                                └──────────── Workspace ID ────────────┘         └──────────── Report ID ────────────┘
```

The **Tenant ID** and **Client ID** come from the Azure AD app registration (set up by IT/admin).

---

## Row-Level Security (RLS) with Embedding

RLS works the same way you already know it — you define roles with DAX filters in Power BI Desktop. The difference is how the role gets applied:

| Scenario | How the role is applied |
|---|---|
| **Power BI Service (normal)** | User logs in → Power BI checks their role membership |
| **Embedded (App Owns Data)** | Your app tells Power BI which role to apply by passing an **EffectiveIdentity** when generating the embed token |

### What your app sends to the API:

```json
{
  "datasets": [{ "id": "<dataset-id>" }],
  "reports": [{ "id": "<report-id>" }],
  "identities": [{
    "username": "alice.smith@contoso.co.uk",
    "roles": ["DynamicRLS"],
    "datasets": ["<dataset-id>"]
  }]
}
```

- **`username`** — matched against `USERPRINCIPALNAME()` or `USERNAME()` in your DAX filter
- **`roles`** — must exactly match the role name(s) defined in Power BI Desktop

### Important rules:

- If the dataset **has** RLS roles → you **must** pass an `EffectiveIdentity` (otherwise the API returns a 400 error)
- If the dataset **does not** have RLS roles → you **must not** pass an `EffectiveIdentity` (otherwise the API returns a 400 error)
- For an "admin" user who should see all data, create a role with no DAX filter (e.g., a role called `AllAccess` with an empty filter expression)

---

## What Your Report Looks Like When Embedded

From the end user's perspective, the embedded report looks and behaves exactly like it does in the Power BI Service:

- **Page tabs** — navigate between report pages
- **Slicers** — filter data interactively
- **Cross-filtering** — click a visual to filter other visuals
- **Drill-through** — right-click → drill through to detail pages
- **Tooltips** — hover for detail
- **Bookmarks** — saved view states

The only difference is it's inside your app's UI, with your branding and navigation around it.

---

## Capacity & Licensing

To embed reports for external users (App Owns Data), you need one of:

| Option | Cost model | Best for |
|---|---|---|
| **Power BI Embedded (A SKU)** | Pay-as-you-go Azure resource | Development, testing, variable workloads |
| **Fabric Capacity (F SKU)** | Monthly commitment | Production, steady workloads |
| **Power BI Premium (P SKU)** | Per-capacity | Organisations already on Premium |

> **For development and testing**, you can use a Pro license with limited API calls. For production, you need dedicated capacity.

---

## Summary

| Concept | What it means for you |
|---|---|
| **Publish reports** | Same as always — Desktop → Publish → Workspace |
| **App registration** | One-time Azure AD setup to give your app API access |
| **Embed token** | Short-lived key generated server-side, scoped to a single report |
| **JS SDK** | Renders the report in the browser — you don't build a viewer |
| **RLS** | Same DAX roles as always, but the app passes the identity instead of Azure AD |
| **No user licenses** | End users don't need Pro/PPU — the capacity handles it |

---

## Further Reading

- [Tutorial: Embed for your customers](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-sample-for-customers)
- [Row-Level Security with Power BI Embedded](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embedded-row-level-security)
- [Embed a report with RLS](https://learn.microsoft.com/en-us/power-bi/developer/embedded/cloud-rls)
- [Power BI Embedded pricing](https://azure.microsoft.com/en-us/pricing/details/power-bi-embedded/)
- [Power BI REST API reference](https://learn.microsoft.com/en-us/rest/api/power-bi/)
