# IMPORTANT: Analytics Uses Separate Credentials

## For Ralph or anyone implementing analytics integration:

### Two LinkedIn Apps Required

1. **Poster App** (existing)
   - Env var: `LINKEDIN_ACCESS_TOKEN`
   - Permission: `w_member_social`
   - Used by: `agents/linkedin/post.py`

2. **Analytics App** (new - needs setup)
   - Env var: `LINKEDIN_ANALYTICS_ACCESS_TOKEN`
   - Permission: `r_organization_social`, `rw_organization_admin`
   - Used by: `agents/linkedin/analytics.py`

### Why Separate?

LinkedIn requires different OAuth apps for different permission scopes. You cannot get analytics permissions on a posting-only app.

### Implementation Requirements

When implementing CLI or any code that uses analytics:

```python
# ❌ WRONG - Don't use posting token for analytics
token = os.getenv("LINKEDIN_ACCESS_TOKEN")

# ✅ CORRECT - Use separate analytics token
token = os.getenv("LINKEDIN_ANALYTICS_ACCESS_TOKEN")
```

### Error Handling

If analytics token is missing, provide helpful error:

```python
if not token:
    print("Error: LINKEDIN_ANALYTICS_ACCESS_TOKEN not set")
    print("Analytics requires a separate LinkedIn app.")
    print("See LINKEDIN_ANALYTICS_SETUP.md for setup instructions.")
    sys.exit(1)
```

### Setup Documentation

Full setup guide: `LINKEDIN_ANALYTICS_SETUP.md`

### Testing Without Analytics App

If you don't have analytics credentials yet, you can:
- Mock the analytics API in tests (required anyway)
- Skip manual testing (tests will cover functionality)
- Document that setup is required before production use

### Current Status

- [ ] Analytics app created on LinkedIn
- [ ] Credentials added to `.env`
- [ ] OAuth flow completed
- [ ] Analytics access tested

User needs to complete setup before analytics will work in production.
