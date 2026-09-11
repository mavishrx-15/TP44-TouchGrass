# Site access on Vercel

Vercel runs `middleware.js` before serving pages and assets. HTTP Basic Auth
prompts visitors for a shared username and password; no application account is
created. Use HTTPS. This gate does not protect the separate Cloud Run API.

## Deploy

1. Use `frontend` as the Vercel project's Root Directory.
2. Add server-side environment variables `SITE_AUTH_USERNAME` (for example,
   `reviewer`) and `SITE_AUTH_PASSWORD` (a long, unique password) to Production
   and Preview. Do not prefix them with `VITE_` or commit their values.
3. Deploy the branch containing this middleware. Apply the change to each branch
   serving a site that needs protection; changing `dev` does not update `main`
   or `iteration1`. Previously created deployments are not retroactively protected.
4. In a private browser window, open the homepage and a direct `/map` URL.
   Both must prompt for credentials. Wrong credentials must fail; correct ones
   must load the app. Verify a direct asset URL also rejects anonymous access.

Missing credentials return 503 rather than exposing the site. Updating credentials
requires redeployment. Browsers remember Basic Auth credentials; use a new private
session to test another password. Local `npm run dev` does not execute this gate.

Run the middleware checks with `node --test tests/middleware.test.js` from
`frontend`. These check the handler; the private-window checks above verify actual
Vercel routing after deployment.
