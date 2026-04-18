"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Nova = void 0;

function tryParseJson(value) {
  if (!value || typeof value !== "string") {
    return {};
  }

  try {
    return JSON.parse(value);
  } catch (error) {
    throw new Error(`Invalid JSON payload: ${error.message}`);
  }
}

function parseCsv(value) {
  if (!value || typeof value !== "string") {
    return [];
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

class Nova {
  constructor() {
    this.description = {
      displayName: "Nova OS",
      name: "nova",
      icon: {
        light: "file:nova_i-dark.png",
        dark: "file:nova_i-light.png",
      },
      group: ["transform"],
      version: 1,
      subtitle: '={{$parameter["resource"] + ": " + $parameter["operation"]}}',
      description: "Governance, ledger verification, and duplicate-safe email checks for Nova OS",
      defaults: {
        name: "Nova OS",
        color: "#111111",
      },
      inputs: ["main"],
      outputs: ["main"],
      credentials: [{ name: "novaApi", required: true }],
      properties: [
        {
          displayName: "Resource",
          name: "resource",
          type: "options",
          noDataExpression: true,
          default: "governance",
          options: [
            { name: "Governance", value: "governance" },
            { name: "Gmail", value: "gmail" },
            { name: "Agents", value: "agents" },
            { name: "Ledger", value: "ledger" },
          ],
        },
        {
          displayName: "Operation",
          name: "operation",
          type: "options",
          noDataExpression: true,
          default: "evaluate",
          displayOptions: { show: { resource: ["governance"] } },
          options: [
            { name: "Evaluate Action", value: "evaluate" },
          ],
        },
        {
          displayName: "Operation",
          name: "operation",
          type: "options",
          noDataExpression: true,
          default: "checkDuplicate",
          displayOptions: { show: { resource: ["gmail"] } },
          options: [
            { name: "Check Duplicate Email", value: "checkDuplicate" },
          ],
        },
        {
          displayName: "Operation",
          name: "operation",
          type: "options",
          noDataExpression: true,
          default: "register",
          displayOptions: { show: { resource: ["agents"] } },
          options: [
            { name: "Register Workflow Agent", value: "register" },
          ],
        },
        {
          displayName: "Operation",
          name: "operation",
          type: "options",
          noDataExpression: true,
          default: "list",
          displayOptions: { show: { resource: ["ledger"] } },
          options: [
            { name: "List Entries", value: "list" },
            { name: "Verify Chain", value: "verify" },
          ],
        },

        {
          displayName: "Managed Agent ID",
          name: "agentId",
          type: "string",
          default: "",
          required: true,
          placeholder: "agent_1234567890abcdef",
          description: "Nova managed agent ID used to evaluate this workflow action.",
          displayOptions: { show: { resource: ["governance"], operation: ["evaluate"] } },
        },
        {
          displayName: "Action",
          name: "action",
          type: "string",
          default: "send_email",
          required: true,
          placeholder: "send_email",
          displayOptions: { show: { resource: ["governance"], operation: ["evaluate"] } },
        },
        {
          displayName: "Payload JSON",
          name: "payloadJson",
          type: "string",
          typeOptions: { rows: 8 },
          default: "{\n  \"recipient\": \"{{$json.email}}\",\n  \"subject\": \"Weekly Newsletter\"\n}",
          required: true,
          displayOptions: { show: { resource: ["governance"], operation: ["evaluate"] } },
        },
        {
          displayName: "Legacy Token ID (Fallback)",
          name: "legacyTokenId",
          type: "string",
          default: "",
          placeholder: "3",
          description: "Optional legacy token used when the target Nova backend exposes /validate instead of /api/evaluate.",
          displayOptions: { show: { resource: ["governance"], operation: ["evaluate"] } },
        },

        {
          displayName: "Recipient Email",
          name: "recipientEmail",
          type: "string",
          default: "",
          required: true,
          placeholder: "user@example.com",
          displayOptions: { show: { resource: ["gmail"], operation: ["checkDuplicate"] } },
        },
        {
          displayName: "Email Subject",
          name: "emailSubject",
          type: "string",
          default: "",
          required: true,
          placeholder: "Weekly Newsletter",
          displayOptions: { show: { resource: ["gmail"], operation: ["checkDuplicate"] } },
        },
        {
          displayName: "Timeframe Hours",
          name: "timeframeHours",
          type: "number",
          default: 24,
          displayOptions: { show: { resource: ["gmail"], operation: ["checkDuplicate"] } },
        },
        {
          displayName: "Block On Duplicate",
          name: "blockOnDuplicate",
          type: "boolean",
          default: true,
          description: "Throw an error when a duplicate email is found so the workflow stops cleanly.",
          displayOptions: { show: { resource: ["gmail"], operation: ["checkDuplicate"] } },
        },

        {
          displayName: "Managed Agent Name",
          name: "managedAgentName",
          type: "string",
          default: "",
          placeholder: "Weekly Newsletter Workflow",
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "Managed Agent Model",
          name: "managedAgentModel",
          type: "string",
          default: "n8n-workflow",
          placeholder: "n8n-workflow",
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "n8n Base URL",
          name: "n8nUrl",
          type: "string",
          default: "http://127.0.0.1:5678",
          placeholder: "http://127.0.0.1:5678",
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "Allowed Permissions (CSV)",
          name: "allowedPermissions",
          type: "string",
          default: "call_agent_api",
          placeholder: "call_agent_api,run_commands",
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "Blocked Permissions (CSV)",
          name: "blockedPermissions",
          type: "string",
          default: "delete_production_db",
          placeholder: "delete_production_db,send_marketing_email",
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "Auto Allow Threshold",
          name: "autoAllowThreshold",
          type: "number",
          default: 30,
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "Escalate Threshold",
          name: "escalateThreshold",
          type: "number",
          default: 60,
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },
        {
          displayName: "Auto Block Threshold",
          name: "autoBlockThreshold",
          type: "number",
          default: 80,
          displayOptions: { show: { resource: ["agents"], operation: ["register"] } },
        },

        {
          displayName: "Limit",
          name: "limit",
          type: "number",
          default: 50,
          displayOptions: { show: { resource: ["ledger"], operation: ["list"] } },
        },
      ],
    };
  }

  async execute() {
    const items = this.getInputData();
    const returnData = [];
    const credentials = await this.getCredentials("novaApi");
    const baseUrl = String(credentials.url || "").replace(/\/$/, "");
    const apiKey = String(credentials.apiKey || "");
    const resource = this.getNodeParameter("resource", 0);
    const operation = this.getNodeParameter("operation", 0);

    const request = async (method, path, body) => this.helpers.request({
      method,
      url: `${baseUrl}${path}`,
      headers: {
        "x-api-key": apiKey,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
      json: true,
    });
    const normalizeLegacyDecision = (verdict) => {
      if (verdict === "APPROVED") {
        return "ALLOW";
      }
      if (verdict === "ESCALATED") {
        return "ESCALATE";
      }
      return "BLOCK";
    };

    const workflow = typeof this.getWorkflow === "function" ? this.getWorkflow() : null;
    const workflowName = workflow && workflow.name ? workflow.name : "Nova n8n Workflow";
    const workflowId = workflow && workflow.id ? workflow.id : null;

    for (let i = 0; i < items.length; i++) {
      try {
        let result = {};

        if (resource === "governance" && operation === "evaluate") {
          const payload = tryParseJson(this.getNodeParameter("payloadJson", i));
          const legacyTokenId = this.getNodeParameter("legacyTokenId", i, "");
          const action = this.getNodeParameter("action", i);
          const runtimeBody = {
            agent_id: this.getNodeParameter("agentId", i),
            action,
            payload,
          };

          try {
            result = await request("POST", "/api/evaluate", runtimeBody);
          } catch (error) {
            const message = String(error && error.message ? error.message : "");
            const statusCode = Number(
              (error && (error.statusCode || error.httpCode))
              || (error && error.cause && (error.cause.statusCode || error.cause.httpCode))
              || 0,
            );
            const apiMissing = statusCode === 404 || /not found/i.test(message);

            if (!legacyTokenId || !apiMissing) {
              throw error;
            }

            const recipient = payload.recipient || payload.email || payload.to || "";
            const subject = payload.subject || "";
            const context = [
              recipient ? `Recipient: ${recipient}` : "",
              subject ? `Subject: ${subject}` : "",
              `Payload: ${JSON.stringify(payload)}`,
            ].filter(Boolean).join(" | ");

            const legacyTokenValue = /^\d+$/.test(String(legacyTokenId))
              ? Number(legacyTokenId)
              : legacyTokenId;

            const legacy = await request("POST", "/validate", {
              token_id: legacyTokenValue,
              action,
              context,
              check_duplicates: false,
              generate_response: false,
              dry_run: false,
            });

            result = {
              ...legacy,
              mode: "legacy_validate",
              decision: {
                action: normalizeLegacyDecision(legacy.verdict),
                reason: legacy.reason || "Legacy validation completed",
              },
              ledger_hash: legacy.hash || legacy.ledger_hash || null,
            };
          }
        }

        if (resource === "gmail" && operation === "checkDuplicate") {
          const recipientEmail = this.getNodeParameter("recipientEmail", i);
          const emailSubject = this.getNodeParameter("emailSubject", i);
          const timeframeHours = this.getNodeParameter("timeframeHours", i);
          result = await request(
            "GET",
            `/api/gmail/check-duplicate?recipient=${encodeURIComponent(recipientEmail)}&subject=${encodeURIComponent(emailSubject)}&timeframe_hours=${encodeURIComponent(timeframeHours)}`,
          );

          if (result && result.is_duplicate && this.getNodeParameter("blockOnDuplicate", i)) {
            throw new Error(
              `Duplicate email detected for ${recipientEmail} with subject "${emailSubject}" at ${result.last_sent_at || "an unknown time"}`,
            );
          }
        }

        if (resource === "agents" && operation === "register") {
          const managedAgentName = this.getNodeParameter("managedAgentName", i) || workflowName;
          result = await request("POST", "/api/agents/create", {
            name: managedAgentName,
            type: "n8n",
            model: this.getNodeParameter("managedAgentModel", i),
            config: {
              n8n_url: this.getNodeParameter("n8nUrl", i),
              workflow_id: workflowId,
              workflow_name: workflowName,
            },
            permissions: {
              can_do: parseCsv(this.getNodeParameter("allowedPermissions", i)),
              cannot_do: parseCsv(this.getNodeParameter("blockedPermissions", i)),
            },
            risk_thresholds: {
              auto_allow: this.getNodeParameter("autoAllowThreshold", i),
              escalate: this.getNodeParameter("escalateThreshold", i),
              auto_block: this.getNodeParameter("autoBlockThreshold", i),
            },
            quota: {
              max_evaluations_per_day: 500,
              max_tokens_per_request: 0,
            },
          });
        }

        if (resource === "ledger" && operation === "list") {
          const limit = this.getNodeParameter("limit", i);
          result = await request("GET", `/api/ledger?limit=${encodeURIComponent(limit)}`);
        }

        if (resource === "ledger" && operation === "verify") {
          result = await request("GET", "/api/ledger/verify");
        }

        returnData.push({
          json: {
            ...items[i].json,
            nova: result,
          },
        });
      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({
            json: {
              ...items[i].json,
              error: error.message,
            },
          });
        } else {
          throw error;
        }
      }
    }

    return [returnData];
  }
}

exports.Nova = Nova;
