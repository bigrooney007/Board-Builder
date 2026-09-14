# Emergent Google Auth — Testing Playbook (Board Fundraising Game)

The app uses Emergent-managed Google OAuth for member sign-in, exchanged for the app's OWN member JWT.
Flow: `/game/signup` → "Sign in with Google" → `https://auth.emergentagent.com/?redirect={origin}/game/start`
→ returns to `{origin}/game/start#session_id=...` → `GoogleAuthGate` in App.js renders `GameAuthCallback`
→ POST `/api/members/google/session` {session_id} → backend calls
`https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data` (header X-Session-ID)
→ finds-or-creates a record in db.members by email → returns member JWT (`member_access_token` cookie + bearer token).

IMPORTANT: After the exchange there is NO separate session_token store — the standard member JWT auth is used
(same as email/password members). To test authenticated game flows, DO NOT try to mock Google;
instead create a member directly:

## Create a game test member (bypasses Google)
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl -s -X POST "$API_URL/api/members/register" -H "Content-Type: application/json" \
  -d '{"first_name":"Game","last_name":"Tester","email":"game-tester@example.com","password":"GameTest123!","confirm_password":"GameTest123!"}'
# → returns {"token": "..."} — use as Bearer token for /api/game/* endpoints
```
Grant the game entitlement without a purchase (Mongo, db test_database):
```bash
mongosh --eval 'use("test_database"); db.members.updateOne({email:"game-tester@example.com"},{$addToSet:{entitlements:"board_fundraising_game"}})'
```

## Google exchange endpoint negative test
```bash
curl -s -X POST "$API_URL/api/members/google/session" -H "Content-Type: application/json" -d '{"session_id":"invalid"}'
# expect 401 "Google sign-in could not be verified"
```

## Checklist
- [ ] `#session_id=` fragment on ANY route renders GameAuthCallback (GoogleAuthGate wraps Routes)
- [ ] /api/members/google/session with invalid id → 401
- [ ] Existing email/password login untouched (POST /api/members/login)
- [ ] Google-created member has password_hash "" and cannot log in with a password
