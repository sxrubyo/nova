# n8n-nodes-nova

Nova OS community node for n8n.

## Supported operations

- `Governance -> Evaluate Action`
  Requires a Nova managed agent ID and calls `/api/evaluate`.
- `Gmail -> Check Duplicate Email`
  Calls `/api/gmail/check-duplicate` and can stop the workflow when a duplicate is found.
- `Agents -> Register Workflow Agent`
  Creates a Nova managed agent through `/api/agents/create`.
- `Ledger -> List Entries`
  Reads recent ledger entries from `/api/ledger`.
- `Ledger -> Verify Chain`
  Verifies ledger integrity via `/api/ledger/verify`.

## Recommended anti-duplicate email flow

1. `Nova OS -> Gmail -> Check Duplicate Email`
2. `IF duplicate = false`
3. `Gmail -> Send Email`
4. `Nova OS -> Governance -> Evaluate Action`

## Example workflow

- Import [`examples/send-email-no-duplicates.workflow.json`](./examples/send-email-no-duplicates.workflow.json) into n8n.
- Replace `agent_replace_me` with the managed agent ID created in Nova.
- Add Gmail credentials to the `Gmail Send` node before enabling the workflow.

## Credentials

- `Nova API URL`: defaults to `http://127.0.0.1:8000`
- `Workspace API Key`: Nova workspace API key used in `x-api-key`
