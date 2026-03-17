const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("appConfig", {
  apiBaseUrl: "http://127.0.0.1:8000"
});
