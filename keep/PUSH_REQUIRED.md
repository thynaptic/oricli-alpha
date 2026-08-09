# Push required

The Keep extract is ready but **this Cloud Agent cannot push** to
`genoventures-labs/Keep` (`cursor[bot]` has no write permission on that org).

## Option A — grant write, then re-run the agent

- Add the Cursor GitHub App to the **genoventures-labs** org, **or**
- Add `cursor[bot]` as a collaborator with **Write** on `Keep`, **or**
- Add a PAT secret (`GENOVENTURES_GH_TOKEN`) with `repo` scope for that org

## Option B — push yourself (history preserved)

From any machine authenticated to Genoventures Labs:

```bash
# Get keep-history.bundle from the agent artifacts, then:
git clone keep-history.bundle Keep -b keep-main
cd Keep
git checkout -B main
git remote add origin https://github.com/genoventures-labs/Keep.git
git push -u origin main
```

Once `main` exists on https://github.com/genoventures-labs/Keep, the agent
will replace in-tree `ori-capsule/` with the `keep/` submodule.
