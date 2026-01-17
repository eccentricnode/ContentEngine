# Get LinkedIn Analytics Access Token - Checklist

## ⏸️ WAITING ON: Community Management API Approval

**Status:** Application submitted, awaiting LinkedIn review (10-14 days typical)

**Why waiting matters:** Without Community Management API approval, you CANNOT:
- Read analytics (impressions, engagement)
- Read comments or reactions
- Use any engagement-related endpoints

**What to do while waiting:**
1. ✅ Code is ready (analytics module, OAuth flow, CLI)
2. ✅ App credentials configured
3. ⏳ Wait for LinkedIn email approval
4. Run OAuth flow AFTER approval to get token

---

## Before Running OAuth Flow (After Approval)

### 1. Check LinkedIn Developer Portal

Go to: https://www.linkedin.com/developers/apps

**Verify your analytics app:**
- [ ] App exists (name: "ContentEngine Analytics" or similar)
- [ ] Client ID matches `.env`: `86qg1oobz35nvh`
- [ ] Client Secret matches `.env`

### 2. Check Products/Permissions

In your analytics app, go to **Products** tab:

**Required products (request if not enabled):**
- [ ] **Share on LinkedIn** (base requirement)
- [ ] **Marketing Developer Platform** OR **Community Management API**
  - This gives you access to analytics endpoints
  - May require LinkedIn Page (not personal profile)

**If products aren't approved:**
- Click "Request access" for each
- LinkedIn usually approves instantly for personal apps
- May need to create a LinkedIn Page first

### 3. Check OAuth Settings

In **Auth** tab:

**Redirect URLs - ADD THIS:**
```
http://localhost:8888/callback
```

**OAuth 2.0 scopes - VERIFY YOU HAVE:**
- `r_basicprofile` or `profile` (read profile)
- `r_organization_social` (read org social data - **KEY FOR ANALYTICS**)
- `w_member_social` (optional - if posting from same app)
- `rw_organization_admin` (optional - for org page analytics)

### 4. LinkedIn Page Requirement

**Important:** Analytics API works best with **LinkedIn Organization Pages**, not personal profiles.

**Do you have a LinkedIn Page?**
- [ ] Yes - I have a LinkedIn Page
- [ ] No - Need to create one

**To create a LinkedIn Page:**
1. Go to: https://www.linkedin.com/company/setup/new/
2. Create Company/Organization page
3. This gives you access to organization analytics

## Running the OAuth Flow

Once the above is confirmed:

```bash
cd ~/Work/ContentEngine

# Load environment
source .env

# Run OAuth flow
python scripts/get_analytics_token.py
```

**What happens:**
1. Browser opens to LinkedIn authorization
2. You approve the app
3. Script receives authorization code
4. Script exchanges code for access token
5. Script prints token to add to `.env`

## After Getting Token

1. Copy the access token from script output
2. Update `.env`:
   ```bash
   LINKEDIN_ANALYTICS_ACCESS_TOKEN="<token_from_script>"
   ```
3. Test analytics:
   ```bash
   uv run content-engine collect-analytics --test-post urn:li:share:7412668096475369472
   ```

## Troubleshooting

### "Invalid redirect_uri"
- Add `http://localhost:8888/callback` to Auth settings
- Make sure it's EXACTLY that URL (no trailing slash)

### "Insufficient permissions"
- App doesn't have analytics products enabled
- Request "Marketing Developer Platform" or "Community Management API"

### "404 Not Found" when fetching analytics
- Post might be from personal profile (not organization page)
- Analytics API requires organization page posts
- Try posting from LinkedIn Page instead

### "Access token expired"
- Tokens expire (usually 60 days)
- Re-run `get_analytics_token.py` to refresh

## Quick Test

After setup, test with your New Year post:

```bash
uv run content-engine collect-analytics --test-post urn:li:share:7412668096475369472
```

**Expected output:**
```
✓ Analytics for urn:li:share:7412668096475369472:
  Impressions: 1,234
  Likes: 45
  Comments: 3
  Engagement Rate: 4.05%
```

## Current Status

- [ ] Analytics app verified on LinkedIn
- [ ] Products approved (Marketing/Community Management)
- [ ] Redirect URI added
- [ ] OAuth scopes confirmed
- [ ] LinkedIn Page created (if needed)
- [ ] OAuth flow completed
- [ ] Access token added to `.env`
- [ ] Analytics tested successfully
