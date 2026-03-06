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

## Row-Level Security (RLS) — Deep Dive

RLS controls which **rows of data** a user sees within a report. You already know how to define it in Power BI Desktop — the key difference with embedding is *how the role gets applied*.

### How RLS normally works vs. embedded

| Scenario | Who decides the user's role? |
|---|---|
| **Power BI Service** | Azure AD login → Power BI checks the user's role membership automatically |
| **Embedded (App Owns Data)** | Your app explicitly tells Power BI which role to apply by passing an **EffectiveIdentity** in the embed token request |

This is powerful because **your app controls the identity**. The end user doesn't need an Azure AD account or a Power BI license — your app maps them to the right role.

### Static vs. Dynamic RLS

| Type | DAX filter example | How `username` is used | When to use |
|---|---|---|---|
| **Static** | `[Region] = "East"` | Ignored (the filter is hardcoded in the role) | Fixed roles like "East region", "West region" |
| **Dynamic** | `[UserUPN] = USERPRINCIPALNAME()` | The `username` value replaces `USERPRINCIPALNAME()` at query time | Many users, each sees their own data slice |

**Dynamic RLS is usually the better choice** because you define one role and let the `username` value do the filtering. You don't need to create a separate role for each user or region.

### How to set it up

1. **In Power BI Desktop → Modeling → Manage Roles:**
   - Create a role (e.g., `DynamicRLS`)
   - Add a DAX filter on your user/security table: `[UserUPN] = USERPRINCIPALNAME()`
   - This means "only show rows where UserUPN matches the identity passed in the token"

2. **In your data model:**
   - You need a table that maps users to the data they should see
   - Example: a `Users` table with `UserUPN` and `ProviderID`, related to your fact tables
   - The RLS filter on the `Users` table cascades through relationships to filter everything

3. **When generating the embed token**, your app passes:

```json
{
  "identities": [{
    "username": "alice.smith@contoso.co.uk",
    "roles": ["DynamicRLS"],
    "datasets": ["<dataset-id>"]
  }]
}
```

4. **Power BI enforces the filter** — the user literally cannot see rows outside their scope, even if they try to manipulate the JS SDK

### The "admin" problem

Once a dataset has any RLS role, the API **requires** an EffectiveIdentity on every token request. There's no way to say "skip RLS for this user." Solutions:

| Approach | How |
|---|---|
| **AllAccess role** | Create a role with no DAX filter (empty expression = no restriction). Pass that role for admin users. |
| **Separate dataset** | Have an admin-specific dataset without RLS defined |
| **DAX logic** | Add a condition like `IF(USERNAME() = "admin", TRUE(), [UserUPN] = USERPRINCIPALNAME())` |

### Common pitfalls

| Problem | Cause | Fix |
|---|---|---|
| 400 "requires effective identity" | Dataset has RLS roles but you didn't pass an identity | Always pass `EffectiveIdentity` when RLS is defined |
| 400 "shouldn't have effective identity" | Dataset has no RLS roles but you passed an identity | Remove the `identities` field from the token request |
| User sees no data | The `username` value doesn't match any rows in the security table | Check the exact value — it's case-sensitive and must match the data |
| User sees all data | The RLS role has no filter, or the relationship chain is broken | Verify relationships between the security table and fact tables |

---

## Embed Tokens — How They Work

An embed token is like a **temporary, scoped key** that grants a browser access to a specific Power BI report. Understanding how they work is important for security and architecture decisions.

### What is an embed token?

When your server calls `POST /GenerateToken`, Power BI returns a JSON Web Token (JWT) that encodes:

- Which **report(s)** the token grants access to
- Which **dataset(s)** are involved
- Which **workspace(s)** are in scope
- The **RLS identity** (if any)
- An **expiry time**

Your server sends this token to the browser, and the Power BI JS SDK uses it to authenticate the iframe.

### Token lifecycle

```
Server                          Browser                         Power BI
  │                                │                                │
  │── Generate embed token ───────►│                                │
  │   (POST /GenerateToken)        │                                │
  │                                │                                │
  │◄── Token (JWT, ~1 hour) ──────│                                │
  │                                │                                │
  │── Send token + embedUrl ──────►│                                │
  │                                │── powerbi.embed() ────────────►│
  │                                │   (passes token via            │
  │                                │    postMessage to iframe)      │
  │                                │                                │
  │                                │◄── Report renders ────────────│
  │                                │                                │
  │                           Token expires after ~1 hour           │
  │                                │                                │
  │── Generate new token ─────────►│                                │
  │                                │── report.setAccessToken() ────►│
  │                                │   (seamless refresh)           │
```

### Key properties

| Property | Value | Why it matters |
|---|---|---|
| **Lifetime** | Default ~1 hour (max configurable) | You need to refresh before expiry to avoid interrupting the user |
| **Scope** | Specific report(s) + dataset(s) + workspace(s) | A token for Report A cannot be used to access Report B |
| **RLS baked in** | The identity is encoded in the token | The browser cannot change the RLS identity — it's server-stamped |
| **Single use intent** | Designed for one embed session | Generate a fresh token for each user session / report load |

### Token refresh

Embed tokens expire. If a user has a report open for more than an hour, the report will stop working unless you refresh the token. The JS SDK supports seamless refresh:

```javascript
// Before the token expires, fetch a new one and update
report.setAccessToken(newToken);
```

Best practice: set a timer to refresh the token a few minutes before expiry.

### Security implications

- **The token never contains your Client Secret** — it's a Power BI-issued JWT, not your credential
- **The browser cannot escalate** — the token is scoped and signed by Power BI
- **RLS cannot be bypassed** — the identity is baked into the token at generation time
- **Tokens are disposable** — if compromised, they expire quickly and are scoped to one report

---

## Workload Isolation — Keeping Clients Separate

When you have multiple clients (tenants) using the same embedded application, you need to ensure:

1. **Client A cannot see Client B's reports or data**
2. **Client A's heavy usage doesn't slow down Client B**
3. **Each client's data is cleanly separated**

There are three main approaches, from simplest to most isolated:

### Approach 1: Shared workspace + RLS

```
┌─────────────────────────────────────────┐
│           Single Workspace              │
│                                         │
│  ┌──────────┐  ┌──────────────────────┐ │
│  │ Report   │  │ Dataset              │ │
│  │ (shared) │  │ (all clients' data)  │ │
│  └──────────┘  │                      │ │
│                │  RLS filters by      │ │
│                │  client/tenant       │ │
│                └──────────────────────┘ │
└─────────────────────────────────────────┘
```

| Aspect | Detail |
|---|---|
| **Data separation** | RLS DAX filters ensure each client only sees their rows |
| **Report separation** | All clients share the same report — same visuals, same pages |
| **Performance isolation** | None — everyone shares the same dataset and capacity |
| **Setup effort** | Low — one report, one dataset, RLS roles |
| **Best for** | Small number of clients, same reporting needs, trusted environment |

**Risk:** If RLS is misconfigured, a client could see another's data. All clients share compute resources.

### Approach 2: Separate workspaces per client

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Client A        │  │  Client B        │  │  Client C        │
│  Workspace       │  │  Workspace       │  │  Workspace       │
│                  │  │                  │  │                  │
│  ┌────┐ ┌─────┐ │  │  ┌────┐ ┌─────┐ │  │  ┌────┐ ┌─────┐ │
│  │Rpt │ │Data │ │  │  │Rpt │ │Data │ │  │  │Rpt │ │Data │ │
│  └────┘ └─────┘ │  │  └────┘ └─────┘ │  │  └────┘ └─────┘ │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

| Aspect | Detail |
|---|---|
| **Data separation** | Complete — each client's data is in a separate dataset in a separate workspace |
| **Report separation** | Each client can have customised reports if needed |
| **Performance isolation** | Partial — workspaces can share the same capacity, but datasets are separate |
| **Setup effort** | Medium — need to provision a workspace per client (can be automated via API) |
| **Best for** | Moderate number of clients, need for per-client customisation |

**How your app handles it:** Map each user to their workspace ID(s). The app queries the right workspace and generates tokens scoped to it. A user mapped to Workspace A physically cannot receive a token for Workspace B.

### Approach 3: Separate capacities per client (or client group)

```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  Capacity 1 (F4)                │  │  Capacity 2 (F8)                │
│                                 │  │                                 │
│  ┌──────────┐  ┌──────────┐    │  │  ┌──────────┐                   │
│  │Client A  │  │Client B  │    │  │  │Client C  │                   │
│  │Workspace │  │Workspace │    │  │  │Workspace │                   │
│  └──────────┘  └──────────┘    │  │  └──────────┘                   │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

| Aspect | Detail |
|---|---|
| **Data separation** | Complete — separate workspaces |
| **Report separation** | Complete — separate workspaces |
| **Performance isolation** | Complete — each capacity has its own compute and memory |
| **Setup effort** | High — need to provision and manage separate Azure resources |
| **Best for** | Large clients, SLA requirements, regulatory compliance |

### Comparison table

| | Shared + RLS | Separate Workspaces | Separate Capacities |
|---|---|---|---|
| **Data isolation** | Logical (DAX filters) | Physical (separate datasets) | Physical (separate datasets) |
| **Performance isolation** | None | Partial | Full |
| **Cost** | Lowest | Medium | Highest |
| **Per-client customisation** | Limited | Full | Full |
| **Risk if misconfigured** | Data leakage via RLS | Lower — wrong workspace = no data | Lowest |
| **Scalability** | Limited by single dataset size | Good | Best |
| **Management overhead** | Low | Medium | High |

### Which should you choose?

- **Starting out / demo / proof of concept** → Shared workspace + RLS
- **Production with multiple clients** → Separate workspaces (most common)
- **Enterprise / regulated / high-SLA** → Separate capacities

You can also **combine approaches** — for example, separate workspaces per client with RLS within each workspace for sub-filtering (e.g., by department within a client).

### Service principal profiles (advanced)

For large-scale multi-tenancy (hundreds of clients), Microsoft recommends **service principal profiles**. Instead of one service principal accessing all workspaces, you create virtual sub-identities — each profile only has access to specific workspaces. This provides:

- **Tighter blast radius** — a compromised profile only affects one client
- **Higher API rate limits** — limits are per-profile, not shared
- **Easier auditing** — API calls are tagged by profile

> **Reference:** [Multi-tenancy with service principal profiles](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-multi-tenancy)

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
