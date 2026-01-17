# LinkedIn Analytics App Setup

## ⚠️ CRITICAL: Community Management API Required

**As of 2023, LinkedIn locked down all analytics/engagement APIs behind Community Management API.**

**What you CANNOT do without Community Management API:**
- ❌ Read post analytics (impressions, engagement, clicks)
- ❌ Read comments on posts
- ❌ Read likes/reactions on posts
- ❌ Automate liking or commenting
- ❌ Access Social Actions APIs (deprecated June 2023)

**What you CAN do without it:**
- ✅ Post content (Share on LinkedIn product)
- ✅ Read your own profile
- ✅ OAuth authentication

**Current Status:** Application submitted, awaiting approval (10-14 days typical)

### Alternative: Member Post Analytics API (NEW 2025)

LinkedIn launched a [Member Post Analytics API](https://www.linkedin.com/posts/brendangahan_linkedin-makes-it-easier-for-creators-to-activity-7353040557893455872-pWrC) for individual creators, but it's **only available through approved third-party vendors**:
- Buffer, Hootsuite, Sprinklr, Metricool, Later, Vista Social, etc.
- Free approval process for vendors
- Could integrate with their APIs instead of direct LinkedIn access

### Alternative: Apply as Approved Vendor

If Community Management API is denied, you can apply to become an approved vendor for Member Post Analytics API:
- Same access as Buffer/Hootsuite
- Requires vendor application approval
- Better for building this as a product (Sales RPG vision)

**References:**
- [Member Post Analytics Launch](https://digiday.com/media/linkedin-makes-it-easier-for-creators-to-track-performance-across-platforms/)
- [Posts API Docs](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2025-11)
- [Comments API Docs](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api?view=li-lms-2025-11)

---

## Why Two Apps?

LinkedIn requires **separate OAuth apps** for different permission scopes:

| App | Purpose | Permissions | Env Variable |
|-----|---------|-------------|--------------|
| **LinkedIn Poster** | Post content | `w_member_social` | `LINKEDIN_ACCESS_TOKEN` |
| **LinkedIn Analyzer** | Read analytics | `r_organization_social`, `rw_organization_admin` | `LINKEDIN_ANALYTICS_ACCESS_TOKEN` |

## Setup LinkedIn Analytics App

### 1. Create New LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Click **"Create app"**
3. Fill in details:
   - **App name:** ContentEngine Analytics
   - **LinkedIn Page:** Your personal page or company page
   - **App logo:** Any logo
   - **Legal agreement:** Check the box

### 2. Request Analytics Product Access

1. In your new app, go to **Products** tab
2. Request access to:
   - ✅ **Share on LinkedIn** (base access)
   - ✅ **Advertising API** (for analytics access)

   OR

   - ✅ **Community Management API** (if available)

3. Wait for approval (usually instant for personal apps)

### 3. Configure OAuth Scopes

1. Go to **Auth** tab
2. Under **OAuth 2.0 scopes**, verify you have:
   - ✅ `r_organization_social` (read org social data)
   - ✅ `rw_organization_admin` (org admin access)
   - ✅ `w_organization_social` (write org social - for context)

### 4. Add Redirect URLs

1. Still in **Auth** tab
2. Under **Redirect URLs**, add:
   ```
   http://localhost:8000/callback
   ```

### 5. Get Credentials

1. Copy **Client ID** and **Client Secret** from **Auth** tab
2. Add to `.env`:

```bash
# LinkedIn Analytics App (separate from poster)
LINKEDIN_ANALYTICS_CLIENT_ID="your_analytics_client_id"
LINKEDIN_ANALYTICS_CLIENT_SECRET="your_analytics_client_secret"
LINKEDIN_ANALYTICS_ACCESS_TOKEN=""  # Will be filled after OAuth flow
LINKEDIN_ANALYTICS_REFRESH_TOKEN=""
```

### 6. Run OAuth Flow

```bash
# Start OAuth server for analytics app
cd ~/Work/ContentEngine
python agents/linkedin/oauth_analytics.py

# Follow browser prompt to authorize
# Token will be saved to .env automatically
```

## Testing Analytics Access

Once configured, test analytics access:

```bash
# Test fetching analytics for a post
source .env
python agents/linkedin/analytics.py fetch urn:li:share:7412668096475369472
```

Expected output:
```
✓ Analytics for urn:li:share:7412668096475369472:
  Impressions: 1,234
  Likes: 45
  Comments: 3
  Shares: 2
  Clicks: 67
  Engagement Rate: 4.05%
```

## Troubleshooting

### "Access token invalid"
- Analytics token expired (expires in 60 days)
- Run OAuth flow again to refresh

### "Insufficient permissions"
- Analytics app doesn't have correct products enabled
- Check Products tab, request Advertising API or Community Management API

### "Application not found"
- Wrong Client ID in .env
- Verify credentials match analytics app (not poster app)

## Current Status

- [ ] LinkedIn Analytics app created
- [ ] Products requested (Advertising API or Community Management)
- [ ] OAuth redirect URL added
- [ ] Credentials added to .env
- [ ] OAuth flow completed
- [ ] Analytics access tested

## Next Steps After Setup

Once analytics app is configured:

```bash
# Collect analytics for recent posts
uv run content-engine collect-analytics

# View analytics dashboard
python scripts/analytics_dashboard.py

# Set up daily cron job
sudo systemctl enable linkedin-analytics.timer
```

## Important Notes

1. **Keep credentials separate** - Don't mix poster and analytics tokens
2. **Different expiration times** - Analytics tokens may have different TTL
3. **Rate limits apply** - LinkedIn has separate rate limits for analytics API
4. **Organization vs Personal** - Analytics work better with LinkedIn Organization pages

## API Documentation

- [LinkedIn Share Statistics API](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/organizations/share-statistics)
- [UGC Post Analytics](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api)
