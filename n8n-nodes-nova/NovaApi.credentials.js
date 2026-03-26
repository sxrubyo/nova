"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NovaApi = void 0;
class NovaApi {
  constructor() {
    this.name = "novaApi";
    this.displayName = "Nova Core API";
    this.properties = [
      { displayName: "Nova Core URL", name: "url", type: "string", default: "http://localhost:9003" },
      { displayName: "API Key", name: "apiKey", type: "string", typeOptions: { password: true }, default: "nova_dev_key" },
    ];
  }
}
exports.NovaApi = NovaApi;
