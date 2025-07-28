# 🔍 Cursor.sh Authentication Traffic Analysis

## 📍 Request Details
- **URL**: `https://authenticator.cursor.sh/email-verification`
- **Email**: `l-3ppwcqw@stu.mit.edu.ge`
- **Method**: POST
- **Status**: 200 OK

## 🔑 Extracted Authentication Tokens

### 1. Pending Authentication Token
```
KyxZ75O8NR9Q7bZiDh1pLBRkc
```
- **Type**: Temporary authentication token
- **Purpose**: Email verification process
- **Risk**: Medium - Short-lived verification token

### 2. Authorization Session ID
```
01K0SZ4W5AN5DDS1T0E42NAP1P
```
- **Type**: Session identifier
- **Purpose**: Track authorization flow
- **Risk**: High - Session hijacking possible

### 3. JWT Access Token
```
eyJhbGciOiJSUzI1NiIsImtpZCI6InNzb19vaWRjX2tleV9wYWlyXzAxSFNaRjIyMFIyMTFLNVlXRllHMzE2TTBLIn0.eyJhdWQiOiJodHRwczovL2FwaS53b3Jrb3MuY29tL3gvYXV0aGtpdCIsImlzcyI6Imh0dHBzOi8vYXBpLndvcmtvcy5jb20veC9hdXRoa2l0Iiwic3ViIjoidXNlcl8wMUpUUjZWVjFIV1NTWlRHMjQySDVNU0NOUSIsInNpZCI6InNlc3Npb25fMDFLMFNaM0pFRzgzUE04MkhCTkUxOFlXVFkiLCJqdGkiOiIwMUswU1ozSkdISkJXQlEyS0pESjZIUkFYWSIsImV4cCI6MTc1MzIxODQ0MCwiaWF0IjoxNzUzMjE4MTQwfQ.C5Pj0kEl2nkJGgVqPVwYF-LHnk1bDUzkXETbc9orv1dDyQyHm0BZCfks3ImZ6dlMFg2Eq5MlfTjKEXpg5VxOsiBz9HNiHYukHt-DxSGr9jDhKAirAXpHZ5Inf3VckMKdd9XkVroktywUHfx--klOFw_I-Shfm3rpRl_dPcYiZP9TfN9VKRruA1HOpDzEmc-x0G_SQP38wrH6Ttp8GxMxSi31Xvjiq4dWosf9BPgqMexZ8I70JYdyMhXSx_YjzsuezTmLHqKvD5Ia8K1o75dydfCaQWz4NgDN7eabC7rzZuAekBH3Z_9_l78Fe2iJO4bg9PU99f-Uo3h-IGMpXxH7PQ
```

#### JWT Header (Decoded):
```json
{
  "alg": "RS256",
  "kid": "sso_oidc_key_pair_01HSZF220R211K5YWFYG316M0K"
}
```

#### JWT Payload (Decoded):
```json
{
  "aud": "https://api.workos.com/x/authkit",
  "iss": "https://api.workos.com/x/authkit",
  "sub": "user_01JTR6VV1HWSSZTG242H5MSCNQ",
  "sid": "session_01K0SZ3JEG83PM82HBNE18YWTY",
  "jti": "01K0SZ3JGHJBWBQ2KJDJ6HRAXY",
  "exp": 1753218440,
  "iat": 1753218140
}
```

### 4. Cloudflare Clearance Token
```
z1VaApW9PRttANs5_1OgTiRzhMY39VKqCgRmeVyiKJk-1739566955-1.2.1.1-[TRUNCATED]
```
- **Type**: Cloudflare security token
- **Purpose**: Bot protection bypass
- **Risk**: Medium - Site access control

### 5. Iron Sealed Tokens

#### __wuid (User ID Token):
```
Fe26.2*1*556dbba700ba3a51b8d9e5c0ccfae13e4e30847d8ac8db23380db82d764f6bff*[ENCRYPTED_DATA]
```

#### __kduid (Key Data Token):
```
Fe26.2*1*82842163d0cf666e0485606f6a9733f8e4df479fc592143ddfff065fa7e2c55e*[ENCRYPTED_DATA]
```

## 🚨 Security Analysis

### Risk Level: **HIGH** 🔴

### Identified Risks:
1. **Active JWT Token**: Valid until 2025-07-23T00:14:00Z
2. **Session Hijacking**: Session ID exposed in traffic
3. **User Identity**: User ID `user_01JTR6VV1HWSSZTG242H5MSCNQ` compromised
4. **Authentication Bypass**: Multiple auth tokens exposed

### User Information:
- **User ID**: `user_01JTR6VV1HWSSZTG242H5MSCNQ`
- **Session ID**: `session_01K0SZ3JEG83PM82HBNE18YWTY`
- **Email**: `l-3ppwcqw@stu.mit.edu.ge`
- **Provider**: WorkOS AuthKit

### Recommendations:
1. **Immediate**: Revoke all exposed tokens
2. **Security**: Implement token rotation
3. **Monitoring**: Set up session monitoring
4. **Prevention**: Use secure transport only

## 🔐 Token Summary

| Token Type       | Status    | Risk Level | Expiry    |
| ---------------- | --------- | ---------- | --------- |
| JWT Access Token | Active    | High       | 5 minutes |
| Session ID       | Active    | High       | Unknown   |
| Auth Token       | Active    | Medium     | Unknown   |
| CF Clearance     | Active    | Medium     | Unknown   |
| Iron Tokens      | Encrypted | Low        | Unknown   |

---
**Analysis completed by MCP Ecosystem Platform Security Scanner**