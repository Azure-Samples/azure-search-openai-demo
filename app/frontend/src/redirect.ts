// Dedicated MSAL redirect-bridge entry point.
// This file is intentionally minimal: per MSAL docs the popup redirect page must
// contain ONLY the bridge script — no routing, no app code.
// See https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/login-user.md#redirecturi-considerations
import { broadcastResponseToMainFrame } from "@azure/msal-browser/redirect-bridge";

broadcastResponseToMainFrame().catch(err => {
    // eslint-disable-next-line no-console
    console.error("MSAL redirect bridge failed", err);
});
