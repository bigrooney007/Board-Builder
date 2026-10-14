# V2 verification record

The source is based on `d627263044f606a819366d3b04fe7e240b8e254d`. All examples and test records are synthetic. Payment, AI and email provider calls are replaced at their transport boundaries; no production database, real charge or real network broadcast is used.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s backend/tests -p 'test_v2*.py'` | 39 passing service/API/methodology/security tests |
| `python tests/validate_v2_contracts.py` | 8 passing preservation/isolation checks |
| `node tests/validate_v2_frontend.cjs` | 18 actual frontend JS/JSX files parse successfully |
| `python -m compileall -q backend` | Pass |
| `git diff --check` | Pass |
| Existing standalone source-contract results against the exact base | Identical, including 8 pre-existing failing validators |
| Frontend production build and React/Jest tests | Not run: project dependencies unavailable |
| Actual desktop/mobile browser tests | Not run: actual frontend build unavailable |
| Real MongoDB/Stripe/Resend/AI integration | Not run: isolated provider configuration required |

Coverage includes four separate $197 purchases; original entitlements/purchases retained; payment replay/wrong amount/wrong journey/live-test isolation; 39 recruitment resources; exact saved branded PDF/DOCX/TXT approvals; edits requiring fresh approval; delivery retries using identical provider keys and bytes; confirmed campaign launch; application activation; isolated marketplace listing; application/CV/guide/invitation/rejection; registered opt-in network selection and permission rechecks; notification links without owner privileges for candidates; private fundraising drafts and multiple funding categories; overlapping audience proposals; explicit adoption and consent; mission retention; approved-only final plans; recommitment invitations/follow-ups/response-derived guide; worker recovery; noindex/no-store error headers; tenant permissions and token expiry/tampering; immutable source submissions; main homepage and original route/price/source preservation.

Actual provider delivery, model writing quality and complete browser acceptance are separate outstanding release checks. Use the fixture and commands in `nbb-v2-handoff.md` to complete those checks in Emergent before any release authorization.
