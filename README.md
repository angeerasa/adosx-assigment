# ADOSX
## How to run it (Windows, PowerShell)

**1. Get Postgres running.**  
(i) Open it using pgAdmin4 after installing both Postgres and pgAdmin4  
(ii) Run the following in QueryTool
```sql
CREATE DATABASE adosx;
CREATE ROLE adosx_owner WITH LOGIN PASSWORD 'adosx_owner' CREATEDB;
CREATE ROLE adosx_app WITH LOGIN PASSWORD 'adosx_app' NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER DATABASE adosx OWNER TO adosx_owner;

GRANT ALL ON SCHEMA public TO adosx_owner;
GRANT USAGE ON SCHEMA public TO adosx_app;
```
(iii) Clone the repo 
```git
git clone https://github.com/angeerasa/adosx-assigment.git
```
(iv) install all the requirements
```powershell
pip install -r requirements.txt
```
**2. Python environment.**  
 Clone the repo 
```git
git clone https://github.com/angeerasa/adosx-assigment.git
```   
and run these commands
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**3. Migrate, load data, reconcile, seed demo users.** All of these are
cross-tenant batch operations and must run as the owner role:

```powershell
$env:DB_ROLE="owner"
python manage.py migrate
python manage.py ingest_csv
python manage.py reconcillation
python manage.py seed_users
Remove-Item Env:DB_ROLE
```

**4. Gemini API Key.**  
***(i)*** Create .env file in the root project folder  
***(ii)*** Create an API Key for Gemini [easily doable online]  
***(iii)***
```dotenv
GEMINI_API_KEY=your_api_key
```

**5. Run the app.** This step must NOT set `DB_ROLE=owner` --
the whole point is that the running app connects as the restricted
`adosx_app` role:

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/. Demo users: `alice` / `alice-pw` (ORG-A),
`bob` / `bob_pw` (ORG-B).

**5. Run the tests**, especially the isolation test:

```powershell
$env:DJANGO_DB_ROLE = "owner"
python manage.py test reconciliation.tests.test_tenant_isolation -v 2
Remove-Item Env:DJANGO_DB_ROLE
```

## What I built

- **Ingest** (`reconciliation/management/commands/ingest_csv.py`): loads
  all three CSVs, normalizes System B's dirty `record_ref` values, and preserves the raw,
  un-normalized value.
- **Reconcile** (`.../reconcillation.py`): compares matched Record/Entry pairs
  and produces one `Discrepancy` row per genuine disagreement, tagged
  with one of 8 reason codes (see below). Explicitly does NOT flag a
  record that is legitimately split across two System B entries whose
  values sum to the System A total -- that is a real case in the data
  (REC-1055) and it is not an error.
- **Tenant isolation**: enforced with Postgres row-level security, not a
  Django queryset filter. `reconciliation/tests/test_tenant_isolation.py`
  bypasses the app entirely, connects directly as the same restricted
  role the app uses.
- **API + UI**: `GET /api/exceptions/?reason_code=...&location_id=...`
  and a plain table over it with two filters.
- **Grounded Q&A**: `POST /api/ask/`, deterministic LLM call answers are built only from rows an
  actual queryset returned and every answer cites the `Discrepancy` ids
  it used. Refuses cleanly when it cannot confidently match the question
  to a reason code or location.

## What I deliberately did not build
 Empty for now
## How I worked with the agent
I used Claude. Uploaded all the 3 csv files along with the requirement docx file
and asked it to generate the complete code base and explain me why it wrote
what it wrote (because I didn't significant prior experience with Django). 

## Reason codes

| Code | Meaning |
|---|---|
| `MISSING_IN_B` | Confirmed in A, no matching entry in B at all |
| `UNMATCHED_B_REFERENCE` | A B entry references a record A does not have |
| `DUPLICATE_ENTRY` | Same entry duplicated in B (not a legitimate split) |
| `VALUE_MISMATCH` | Recorded value disagrees between the two systems |
| `MISSING_VALUE` | B has an entry but its value field is blank |
| `LOCATION_MISMATCH` | The two systems disagree on which location |
| `DATE_MISMATCH` | The two systems disagree on the date |
