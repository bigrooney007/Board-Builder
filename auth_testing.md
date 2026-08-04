# Administrator Authentication Testing

1. Confirm the single seeded user has role `admin`, the configured email, and a bcrypt password hash.
2. Confirm the unique `users.email` index and `login_attempts.identifier` index exist.
3. POST `/api/auth/login` with the administrator credentials and retain the HTTP-only cookies.
4. GET `/api/auth/me` with those cookies and confirm the administrator identity.
5. Confirm `/api/admin/*` returns 401 without cookies and succeeds with valid cookies.
6. Confirm there is no registration, public login, applicant login, password reset, or additional administrator endpoint.
7. Confirm five invalid attempts trigger a 15-minute lockout and a successful login clears attempts.