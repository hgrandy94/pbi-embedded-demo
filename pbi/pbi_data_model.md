# Data Model Overview

This model supports provider-specific reporting with dynamic RLS. It contains four tables in a star-schema layout: one fact table and three dimensions.

## Fact Table
**Fact_Reports**  
Contains transactional report records.  
Key fields: `ReportID`, `ProviderID` (FK -> Dim_Provider), `DateID` (FK -> Dim_Date), `ReportType`, `Status`, and metrics: Cost, Revenue, ClaimCount, UtilizationRate, ReportViews.

It drives the analytical reporting.

## Dimension Tables

**Dim_Provider**  
List of provider/service categories. Fields: `ProviderID` (PK), `ProviderName`.

**Dim_Date**  
Calendar table for time intelligence. Fields: `DateID` (PK, YYYYMMDD), `FullDate`, `DayOfWeek`, `Month`, `MonthName`, `Quarter`, `Year`.

**Dim_User**  
Used for dynamic row-level security. Fields: `UserID` (PK), `UserName`, `UserUPN` (must match username passed via embedding), `ProviderID` (FK -> Dim_Provider).

## Relationships

1. Dim_Provider (1) -> (∞) Fact_Reports
2. Dim_Date (1) -> (∞) Fact_Reports
3. Dim_User (∞) -> (1) Dim_Provider

Enables: provider join to Fact_ and time join, dynamic RLS mapping.

## Row-Level Security

The RLS role (for example 'DynamicRLS') applies:

```DAX
Dim_User[UserUPN] = USERPRINCIPALNAME()
```

This filters: Dim_User -> Dim_Provider -> Fact_Reports. Each user sees data for their own provider.
