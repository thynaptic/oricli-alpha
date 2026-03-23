# PocketBase External API Guide

This guide provides technical instructions for AI agents and developers to interact with the PocketBase API externally.

## 🌐 Endpoint & Connectivity
- **Base URL:** `https://pocketbase.thynaptic.com`
- **Admin UI:** `https://pocketbase.thynaptic.com/_/`
- **Reverse Proxy:** Caddy (TLS enabled via Cloudflare).

## 🔐 Authentication (PocketBase v0.23+)
**CRITICAL:** Do NOT use the `Admin` prefix in the Authorization header. Use the raw token string only.

### 1. Authenticate as Admin
To perform administrative tasks (like creating collections), you must first obtain an admin token.

```bash
curl -X POST https://pocketbase.thynaptic.com/api/admins/auth-with-password \
     -H "Content-Type: application/json" \
     -d '{"identity":"cass@thynaptic.com", "password":"nFj1VXlle3vMjYX"}'
```

### 2. Using the Token
Include the returned `token` in the `Authorization` header of subsequent requests:
`Authorization: YOUR_TOKEN_HERE`

---

## 🏗️ Collection Management
To create a new collection, send a `POST` request to `/api/collections`.

### ⚠️ Critical Requirement: JSON Fields
In this version of PocketBase, all `json` type fields **MUST** have a `maxSize` defined in their options, or the request will fail with a `400 Bad Request`.

**Example: Creating a Generic Collection**
```bash
curl -X POST https://pocketbase.thynaptic.com/api/collections \
     -H "Authorization: <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "example_collection",
       "type": "base",
       "schema": [
         {
           "name": "title",
           "type": "text",
           "required": true
         },
         {
           "name": "metadata",
           "type": "json",
           "options": { "maxSize": 2000000 }
         }
       ],
       "listRule": "@request.auth.id != \"\"",
       "viewRule": "@request.auth.id != \"\"",
       "createRule": "@request.auth.role = \"commander\"",
       "updateRule": "@request.auth.role = \"commander\"",
       "deleteRule": null
     }'
```

---

## 👤 User Management
The `users` collection in this instance has been extended with a mandatory schema.

### ⚠️ Critical Requirement: Role Field
All user records **MUST** include a `role` field. Failure to include this will result in a `400 Bad Request`.

- **Field Name:** `role`
- **Allowed Values:** `"commander"`, `"operator"`, `"analyst"`

**Example: Creating a New User**
```bash
curl -X POST https://pocketbase.thynaptic.com/api/collections/users/records \
     -H "Content-Type: application/json" \
     -d '{
       "email": "new_user@example.com",
       "password": "password12345",
       "passwordConfirm": "password12345",
       "username": "user_xyz",
       "role": "operator"
     }'
```

---

## 🛠️ Troubleshooting Common Errors
- **401 Unauthorized:** Ensure the `Authorization` header contains ONLY the token (no "Admin" or "Bearer" prefix).
- **400 Bad Request (Data):** 
    - Check if `role` is missing for users.
    - Check if `maxSize` is missing for any `json` fields in a collection schema.
    - Ensure field names are lowercase and do not contain special characters.
