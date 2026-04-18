# ORI Agent Bootstrap Key V1

This document defines a safer bootstrap path for trusted build agents.

## Why This Exists

Right now there are only two practical ways to mint first-party product keys:

- use the internal `ORI_APP_REG_TOKEN` with `POST /v1/app/register`
- use an admin path that can mint arbitrary tenant keys

Neither is appropriate to hand to a general-purpose agent.

The goal of this design is to let trusted agents build freely without exposing:

- the first-party registration token
- admin credentials
- arbitrary scope selection

## Core Idea

Introduce a new narrow credential type:

- `agb.<prefix>.<secret>`

This is an **agent bootstrap key**, not a runtime key.

It can do exactly one thing:

- call a constrained bootstrap route that mints a normal `glm.*` product key

It cannot:

- call chat
- call spaces
- call email
- call admin routes
- choose arbitrary scopes

## V1 Route

### `POST /v1/agent/register`

Purpose:

- allow a trusted build agent to request a product-scoped runtime key for a specific allowed product

Auth:

- `Authorization: Bearer agb.<prefix>.<secret>`

Request:

```json
{
  "app_name": "ORI Mobile",
  "device_id": "mobile-safe-a"
}
```

Response:

```json
{
  "api_key": "glm.xxx.yyy",
  "base_url": "https://glm.thynaptic.com/v1",
  "scopes": ["runtime:chat", "runtime:email:send", "runtime:models"]
}
```

## V1 Rules

The bootstrap key should be policy-bound.

Recommended V1 policy fields:

- `allowed_apps`
- `max_uses`
- `expires_at`
- `issuer`
- `notes`

Example policy:

```json
{
  "allowed_apps": ["ori-mobile"],
  "max_uses": 5,
  "issuer": "mike",
  "notes": "Trusted mobile build agent bootstrap"
}
```

## What The Bootstrap Key Can Do

- mint approved first-party product keys
- only for apps in its allowlist
- only through `POST /v1/agent/register`
- optionally only for a bounded number of uses

## What The Bootstrap Key Cannot Do

- mint admin keys
- mint arbitrary tenant keys
- request custom scopes
- hit runtime endpoints directly
- use hidden internal products unless explicitly allowed

## Why This Is Safer

This preserves the current runtime truth:

- product runtime keys are still normal `glm.*` keys
- runtime scopes are still enforced the same way
- product app registration logic still defines the final scopes

But it removes the dangerous part:

- agents no longer need the shared internal `ORI_APP_REG_TOKEN`

## Implementation Shape

### 1. New record type

Add a second stored key family for bootstrap keys:

- token format: `agb.<prefix>.<secret>`
- hashed and stored the same way as runtime keys
- policy attached to record

Suggested record fields:

- `prefix`
- `hash`
- `status`
- `allowed_apps`
- `max_uses`
- `use_count`
- `expires_at`
- `issuer`

### 2. New auth path

Add a bootstrap-key authenticator parallel to runtime key auth:

- runtime keys continue to use `glm.*`
- bootstrap keys use `agb.*`

These should not share scopes or context by accident.

### 3. New route

Add:

- `POST /v1/agent/register`

Behavior:

1. authenticate `agb.*`
2. validate product against bootstrap policy
3. derive tenant ID using the same current product rule:
   - `app:<normalized-app-name>`
   - append `:<device_id>` if present
4. reuse the existing `appRegistrationScopes(...)`
5. mint a normal `glm.*` runtime key
6. increment bootstrap key use count
7. log issuance

### 4. Admin issuance

Add one admin-only route to mint bootstrap keys:

- `POST /v1/admin/agent-keys`

This route should create `agb.*` keys with the selected policy.

## Logging Requirements

Every bootstrap use should log:

- bootstrap key id
- issuer
- app_name
- device_id
- resulting tenant id
- resulting runtime scopes
- timestamp

This matters more than convenience.

## MCP Fit

Yes, this fits ORI MCP well.

The clean way is:

- keep raw bootstrap key creation out of public MCP
- allow a trusted internal MCP host to call a dedicated tool later:
  - `register_first_party_app`

That MCP tool should:

- require an `agb.*` key behind the MCP host
- only expose allowed products
- return the normal runtime key and scope set

This gives trusted agents a clean build path without teaching public agents a dangerous bootstrap story.

## Good V1 Boundaries

Start narrow:

- allow `ORI Mobile`
- maybe allow `ORI Home`
- do not allow arbitrary products
- do not allow `ORI Red`
- do not allow admin/runtime wildcards

## Recommendation

Build this as a narrow internal bootstrap product:

- yes for trusted agents
- no for public self-serve
- normal `glm.*` keys stay the runtime contract
- `agb.*` only exists to safely bridge trusted agents into that contract
