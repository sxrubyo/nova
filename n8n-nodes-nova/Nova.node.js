"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Nova = void 0;
class Nova {
  constructor() {
    this.description = {
      displayName: "Nova", name: "nova", group: ["transform"], version: 1,
      subtitle: '={{$parameter["resource"] + ": " + $parameter["operation"]}}',
      description: "Gobernanza de agentes IA — reglas, validación, ledger",
      defaults: { name: "Nova" }, inputs: ["main"], outputs: ["main"],
      credentials: [{ name: "novaApi", required: true }],
      properties: [
        { displayName: "Recurso", name: "resource", type: "options", noDataExpression: true,
          options: [
            { name: "Validar", value: "validate" }, { name: "Reglas", value: "rules" },
            { name: "Ledger", value: "ledger" }, { name: "Interceptar", value: "intercept" },
            { name: "Boot", value: "boot" }, { name: "Stats", value: "stats" },
          ], default: "validate" },
        { displayName: "Operación", name: "operation", type: "options", noDataExpression: true,
          displayOptions: { show: { resource: ["validate"] } },
          options: [{ name: "Validar acción", value: "single" }, { name: "Lote", value: "batch" }],
          default: "single" },
        { displayName: "Acción", name: "action", type: "string", default: "",
          displayOptions: { show: { resource: ["validate"], operation: ["single"] } } },
        { displayName: "Agente", name: "agentName", type: "string", default: "melissa" },
        { displayName: "Contexto", name: "context", type: "string", default: "",
          displayOptions: { show: { resource: ["validate"], operation: ["single"] } } },
        { displayName: "Operación", name: "operation", type: "options", noDataExpression: true,
          displayOptions: { show: { resource: ["rules"] } },
          options: [{ name: "Listar", value: "list" }, { name: "Crear", value: "create" }, { name: "Eliminar", value: "delete" }],
          default: "list" },
        { displayName: "Scope", name: "scope", type: "string", default: "global",
          displayOptions: { show: { resource: ["rules"], operation: ["list"] } } },
        { displayName: "Nombre", name: "ruleName", type: "string", default: "",
          displayOptions: { show: { resource: ["rules"], operation: ["create"] } } },
        { displayName: "Instrucción", name: "ruleInstruction", type: "string", default: "",
          displayOptions: { show: { resource: ["rules"], operation: ["create"] } } },
        { displayName: "Acción", name: "ruleAction", type: "options",
          options: [{ name: "Bloquear", value: "block" }, { name: "Advertir", value: "warn" }],
          default: "block", displayOptions: { show: { resource: ["rules"], operation: ["create"] } } },
        { displayName: "Scope regla", name: "ruleScope", type: "string", default: "global",
          displayOptions: { show: { resource: ["rules"], operation: ["create"] } } },
        { displayName: "Keywords (coma)", name: "keywords", type: "string", default: "",
          displayOptions: { show: { resource: ["rules"], operation: ["create"] } } },
        { displayName: "Rule ID", name: "ruleId", type: "string", default: "",
          displayOptions: { show: { resource: ["rules"], operation: ["delete"] } } },
        { displayName: "Operación", name: "operation", type: "options", noDataExpression: true,
          displayOptions: { show: { resource: ["ledger"] } },
          options: [{ name: "Ver entradas", value: "list" }], default: "list" },
        { displayName: "Límite", name: "limit", type: "number", default: 50,
          displayOptions: { show: { resource: ["ledger"], operation: ["list"] } } },
        { displayName: "Operación", name: "operation", type: "options", noDataExpression: true,
          displayOptions: { show: { resource: ["intercept"] } },
          options: [{ name: "Crear regla desde NL", value: "create" }], default: "create" },
        { displayName: "Mensaje", name: "interceptMessage", type: "string", default: "",
          displayOptions: { show: { resource: ["intercept"], operation: ["create"] } } },
        { displayName: "Scope", name: "interceptScope", type: "string", default: "global",
          displayOptions: { show: { resource: ["intercept"], operation: ["create"] } } },
        { displayName: "Operación", name: "operation", type: "options", noDataExpression: true,
          displayOptions: { show: { resource: ["boot"] } },
          options: [{ name: "Cargar reglas", value: "load" }], default: "load" },
        { displayName: "Operación", name: "operation", type: "options", noDataExpression: true,
          displayOptions: { show: { resource: ["stats"] } },
          options: [{ name: "Ver stats", value: "get" }], default: "get" },
      ],
    };
  }
  async execute() {
    const items = this.getInputData();
    const returnData = [];
    const creds = await this.getCredentials("novaApi");
    const base = creds.url.replace(/\/$/, "");
    const apiKey = creds.apiKey;
    const resource = this.getNodeParameter("resource", 0);
    const operation = this.getNodeParameter("operation", 0);
    const req = async (method, path, body) => this.helpers.request({
      method, url: `${base}${path}`,
      headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined, json: true,
    });
    for (let i = 0; i < items.length; i++) {
      try {
        let result;
        if (resource === "validate" && operation === "single") {
          result = await req("POST", "/validate", {
            action: this.getNodeParameter("action", i),
            agent_name: this.getNodeParameter("agentName", i),
            scope: `agent:${this.getNodeParameter("agentName", i)}`,
            context: this.getNodeParameter("context", i),
            dry_run: false, check_dups: false,
          });
        }
        if (resource === "rules" && operation === "list") {
          result = await req("GET", `/rules?scope=${encodeURIComponent(this.getNodeParameter("scope", i))}`);
        }
        if (resource === "rules" && operation === "create") {
          const kws = this.getNodeParameter("keywords", i).split(",").map(k => k.trim()).filter(Boolean);
          result = await req("POST", "/rules", {
            name: this.getNodeParameter("ruleName", i),
            original_instruction: this.getNodeParameter("ruleInstruction", i),
            action: this.getNodeParameter("ruleAction", i),
            scope: this.getNodeParameter("ruleScope", i),
            source: "n8n", active: true, priority: 7,
            deterministic: { keywords_block: kws, keywords_warn: [], regex_block: [], exact_block: [], max_amount: null },
            semantic: { enabled: false, description: "", threshold: 0.82 },
            message: `No permitido: ${this.getNodeParameter("ruleInstruction", i)}`,
            escalate_to: "", log: true, notify: [],
          });
        }
        if (resource === "rules" && operation === "delete") {
          result = await req("DELETE", `/rules/${this.getNodeParameter("ruleId", i)}`);
        }
        if (resource === "ledger" && operation === "list") {
          const agent = this.getNodeParameter("agentName", i);
          const limit = this.getNodeParameter("limit", i);
          result = await req("GET", `/ledger?agent=${agent}&limit=${limit}`);
        }
        if (resource === "intercept" && operation === "create") {
          result = await req("POST", "/intercept", {
            message: this.getNodeParameter("interceptMessage", i),
            scope: this.getNodeParameter("interceptScope", i),
            sender: "n8n",
          });
        }
        if (resource === "boot" && operation === "load") {
          result = await req("GET", `/boot/${encodeURIComponent(this.getNodeParameter("agentName", i))}`);
        }
        if (resource === "stats" && operation === "get") {
          const agent = this.getNodeParameter("agentName", i);
          result = await req("GET", `/stats${agent ? "?agent=" + agent : ""}`);
        }
        returnData.push({ json: result || {} });
      } catch (error) {
        if (this.continueOnFail()) { returnData.push({ json: { error: error.message } }); }
        else throw error;
      }
    }
    return [returnData];
  }
}
exports.Nova = Nova;
