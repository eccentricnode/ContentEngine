/**
 * Test LinkedIn Connection
 *
 * Verifies your access token works by calling /v2/me
 * Run this BEFORE attempting to post:
 *   bun run test-connection.ts
 */

const ACCESS_TOKEN = process.env.LINKEDIN_ACCESS_TOKEN;

if (!ACCESS_TOKEN) {
  console.error("❌ Missing LINKEDIN_ACCESS_TOKEN in environment");
  console.error("Run oauth-server.ts first to get tokens");
  process.exit(1);
}

console.log("\n🔍 Testing LinkedIn Connection...\n");

// Test with /v2/userinfo endpoint (works with openid profile)
const response = await fetch("https://api.linkedin.com/v2/userinfo", {
  headers: {
    Authorization: `Bearer ${ACCESS_TOKEN}`,
  },
});

if (!response.ok) {
  const errorText = await response.text();
  console.error("❌ Connection failed:", response.status, response.statusText);
  console.error("Response:", errorText);

  if (response.status === 401) {
    console.error("\n💡 Token may be expired. Run oauth-server.ts again.");
  }
  process.exit(1);
}

const userInfo = await response.json();

console.log("✅ Connection successful!\n");
console.log("User Info:");
console.log("  Sub (ID):", userInfo.sub);
console.log("  Name:", userInfo.name);
console.log("  Email:", userInfo.email || "not provided");

// Save the user sub for posting (this is needed for the author URN)
const envPath = ".env";
const envContent = await Bun.file(envPath).text();

if (!envContent.includes("LINKEDIN_USER_SUB")) {
  await Bun.write(envPath, envContent + `\nLINKEDIN_USER_SUB=${userInfo.sub}\n`);
  console.log("\n✅ User ID saved to .env as LINKEDIN_USER_SUB");
}

console.log("\n🎉 Ready to post! Run: bun run post.ts \"Your message here\"");
