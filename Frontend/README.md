# MODELISE Console

A web console for two MODELISE services only:

- **Guardrail Layer 2** (cost guard, your rulebook, local model)
- **Geo Policy Engine** (one rulebook per country or regulation)

Pages: Test prompts, Guardrail rules, Country packs, Spend and limits, Connections.

## What you need first

- Node.js 20.19 or newer (22 is best). Check with `node -v`.
- Both services set up as in your main README.
- LM Studio (or Ollama) running with your judge model, otherwise Guardrail cannot decide and will refuse every prompt.

## Run it (Windows PowerShell)

Open three terminals.

**Terminal 1: Guardrail Layer 2**

    cd guardrail_layer2
    .\venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload --port 8001

**Terminal 2: Geo Policy Engine**

    cd geo_policy_engine
    .\venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload --port 8000

**Terminal 3: this console**

    cd modelise-console
    npm install
    npm run dev

Open http://localhost:5174

## First steps in the app

1. Go to **Connections**. Both services should say Online. If your ports differ, type the right address and press Use address.
2. Sign in to each service with the ADMIN_USERNAME and ADMIN_PASSWORD from that service's own `.env`. Logins are separate for each service.
3. Go to **Test prompts** and run a prompt. Testing works even without signing in.

## Notes

- Nothing else is needed: no database and no extra backend. The browser calls the two services directly (both already allow that).
- Logins are kept for the open tab only. Addresses and your last 20 tests stay in this browser.
- Changing the blocking threshold on Guardrail rules applies straight away but resets when the service restarts.
- Uploading a CSV to Guardrail (or to an existing pack) replaces every rule there. PDFs are added on top.

## Build for hosting

    npm run build

The finished site is in `dist/`. Any static host works. If you host it on another address, that is fine, since both services allow any origin.

## Where things live

    src/lib/api.js           every call to the two services
    src/lib/verdict.js       turns raw answers into allowed / blocked / error
    src/lib/connections.jsx  addresses, logins, online checks
    src/pages/               one file per page
    src/components/          shared pieces (result card, distance meter, dialogs)
    src/styles/              colours and layout (change colours in tokens.css)
