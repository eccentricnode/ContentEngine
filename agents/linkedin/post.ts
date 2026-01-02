/**
 * Post to LinkedIn
 *
 * Usage:
 *   bun run post.ts "Your post content here"
 *   bun run post.ts --dry-run "Test without posting"
 */

const ACCESS_TOKEN = process.env.LINKEDIN_ACCESS_TOKEN;
const USER_SUB = process.env.LINKEDIN_USER_SUB;

if (!ACCESS_TOKEN || !USER_SUB) {
  console.error("❌ Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_USER_SUB");
  console.error("Run oauth-server.ts and test-connection.ts first");
  process.exit(1);
}

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const content = args.filter(a => a !== "--dry-run").join(" ");

if (!content) {
  console.error("❌ No content provided");
  console.error("Usage: bun run post.ts \"Your post content here\"");
  console.error("       bun run post.ts --dry-run \"Test without posting\"");
  process.exit(1);
}

const postBody = {
  author: `urn:li:person:${USER_SUB}`,
  lifecycleState: "PUBLISHED",
  specificContent: {
    "com.linkedin.ugc.ShareContent": {
      shareCommentary: {
        text: content,
      },
      shareMediaCategory: "NONE",
    },
  },
  visibility: {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
  },
};

console.log("\n📝 LinkedIn Post\n");
console.log("Content:", content);
console.log("Length:", content.length, "/ 3000 chars");
console.log("Visibility: PUBLIC");
console.log("Author URN:", postBody.author);

if (dryRun) {
  console.log("\n🧪 DRY RUN - Not actually posting");
  console.log("\nRequest body:");
  console.log(JSON.stringify(postBody, null, 2));
  process.exit(0);
}

console.log("\n🚀 Posting...\n");

const response = await fetch("https://api.linkedin.com/v2/ugcPosts", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${ACCESS_TOKEN}`,
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0",
  },
  body: JSON.stringify(postBody),
});

if (!response.ok) {
  const errorText = await response.text();
  console.error("❌ Post failed:", response.status, response.statusText);
  console.error("Response:", errorText);

  if (response.status === 401) {
    console.error("\n💡 Token may be expired. Run oauth-server.ts again.");
  }
  process.exit(1);
}

const postId = response.headers.get("X-RestLi-Id");
console.log("✅ Posted successfully!");
console.log("Post ID:", postId);
console.log("\nView at: https://www.linkedin.com/feed/");
