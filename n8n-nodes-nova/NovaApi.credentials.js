"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NovaApi = void 0;

class NovaApi {
  constructor() {
    this.name = "novaApi";
    this.displayName = "Nova OS API";
    this.properties = [
      {
        displayName: "Nova API URL",
        name: "url",
        type: "string",
        default: "http://127.0.0.1:8000",
      },
      {
        displayName: "Workspace API Key",
        name: "apiKey",
        type: "string",
        typeOptions: { password: true },
        default: "",
      },
    ];
  }
}

exports.NovaApi = NovaApi;
