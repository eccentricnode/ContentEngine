/**
 * LinkedIn OAuth 2.0 Server
 *
 * Run once to authenticate and save tokens:
 *   bun run oauth-server.ts
 *
 * Opens browser, catches callback, saves tokens to .env
 */

import { $ } from "bun";

const CLIENT_ID = process.env.LINKEDIN_CLIENT_ID;
const CLIENT_SECRET = process.env.LINKEDIN_CLIENT_SECRET;
const REDIRECT_URI = "http://localhost:3000/callback";
const SCOPES = ["openid", "profile", "w_member_social"].join(" ");

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error("Missing LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET in environment");
  console.error("Create a .env file with these values first");
  process.exit(1);
}

const authUrl = new URL("https://www.linkedin.com/oauth/v2/authorization");
authUrl.searchParams.set("response_type", "code");
authUrl.searchParams.set("client_id", CLIENT_ID);
authUrl.searchParams.set("redirect_uri", REDIRECT_URI);
authUrl.searchParams.set("scope", SCOPES);
authUrl.searchParams.set("state", crypto.randomUUID());

console.log("\n🔐 LinkedIn OAuth Flow\n");
console.log("Opening browser for authorization...\n");

// Open browser
await $`xdg-open ${authUrl.toString()}`.quiet();

// Start server to catch callback
const server = Bun.serve({
  port: 3000,
  async fetch(req) {
    const url = new URL(req.url);

    if (url.pathname === "/callback") {
      const code = url.searchParams.get("code");
      const error = url.searchParams.get("error");

      if (error) {
        console.error("❌ Authorization denied:", error);
        server.stop();
        return new Response(`Authorization denied: ${error}`, { status: 400 });
      }

      if (!code) {
        return new Response("No code received", { status: 400 });
      }

      console.log("✅ Authorization code received, exchanging for tokens...\n");

      // Exchange code for tokens
      const tokenResponse = await fetch("https://www.linkedin.com/oauth/v2/accessToken", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          grant_type: "authorization_code",
          code,
          client_id: CLIENT_ID!,
          client_secret: CLIENT_SECRET!,
          redirect_uri: REDIRECT_URI,
        }),
      });

      if (!tokenResponse.ok) {
        const errorText = await tokenResponse.text();
        console.error("❌ Token exchange failed:", errorText);
        server.stop();
        return new Response(`Token exchange failed: ${errorText}`, { status: 500 });
      }

      const tokens = await tokenResponse.json();

      console.log("✅ Tokens received!\n");
      console.log("Access Token:", tokens.access_token?.substring(0, 20) + "...");
      console.log("Expires in:", tokens.expires_in, "seconds");

      // Check for id_token (JWT with user info)
      let userId = "";
      if (tokens.id_token) {
        console.log("ID Token: present");
        // Decode JWT payload (middle part)
        const payload = JSON.parse(Buffer.from(tokens.id_token.split('.')[1], 'base64').toString());
        console.log("User Sub:", payload.sub);
        console.log("Name:", payload.name);
        userId = payload.sub;
      }

      // Save to .env
      const envContent = `# LinkedIn OAuth Tokens - Generated ${new Date().toISOString()}
LINKEDIN_CLIENT_ID=${CLIENT_ID}
LINKEDIN_CLIENT_SECRET=${CLIENT_SECRET}
LINKEDIN_ACCESS_TOKEN=${tokens.access_token}
LINKEDIN_REFRESH_TOKEN=${tokens.refresh_token || ""}
LINKEDIN_TOKEN_EXPIRES=${Date.now() + (tokens.expires_in * 1000)}
LINKEDIN_USER_SUB=${userId}
`;

      await Bun.write(".env", envContent);
      console.log("\n✅ Tokens saved to .env\n");
      console.log("You can now run: bun run test-connection.ts");

      server.stop();
      return new Response(`
        <html>
          <body style="font-family: system-ui; padding: 40px; text-align: center;">
            <h1>✅ Authorization Successful!</h1>
            <p>Tokens have been saved. You can close this window.</p>
          </body>
        </html>
      `, { headers: { "Content-Type": "text/html" } });
    }

    return new Response("LinkedIn OAuth Server", { status: 200 });
  },
});

console.log(`Server running at http://localhost:${server.port}`);
console.log("Waiting for callback...\n");
