import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { randomUUID } from "node:crypto";

const HOST = process.env.HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 3000);
const PUBLIC_ROOT = process.cwd();

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

class InMemoryRunStore {
  constructor() {
    this.runs = new Map();
  }

  async create(run) {
    this.runs.set(run.id, run);
    return run;
  }

  async update(id, updates) {
    const existing = this.runs.get(id);
    if (!existing) {
      return null;
    }

    const nextRun = {
      ...existing,
      ...updates,
    };
    this.runs.set(id, nextRun);
    return nextRun;
  }

  async list() {
    return [...this.runs.values()].sort((left, right) =>
      right.createdAt.localeCompare(left.createdAt)
    );
  }

  async get(id) {
    return this.runs.get(id) ?? null;
  }
}

class SupabaseRunStore {
  constructor({ url, key, table }) {
    this.url = url.replace(/\/$/, "");
    this.key = key;
    this.table = table;
    this.headers = {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    };
  }

  async create(run) {
    await this.request(`/${this.table}`, {
      method: "POST",
      headers: {
        ...this.headers,
        Prefer: "return=representation",
      },
      body: JSON.stringify([serializeRun(run)]),
    });
    return run;
  }

  async update(id, updates) {
    const response = await this.request(
      `/${this.table}?id=eq.${encodeURIComponent(id)}`,
      {
        method: "PATCH",
        headers: {
          ...this.headers,
          Prefer: "return=representation",
        },
        body: JSON.stringify(serializeRun(updates)),
      }
    );

    return response[0] ? deserializeRun(response[0]) : null;
  }

  async list() {
    const rows = await this.request(
      `/${this.table}?select=*&order=created_at.desc`
    );
    return rows.map(deserializeRun);
  }

  async get(id) {
    const rows = await this.request(
      `/${this.table}?select=*&id=eq.${encodeURIComponent(id)}`
    );
    return rows[0] ? deserializeRun(rows[0]) : null;
  }

  async request(pathname, options = {}) {
    const response = await fetch(`${this.url}/rest/v1${pathname}`, options);

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Supabase request failed: ${response.status} ${body}`);
    }

    if (response.status === 204) {
      return [];
    }

    return response.json();
  }
}

const store = createStore();
const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host}`);

    if (url.pathname.startsWith("/api/")) {
      await handleApi(request, response, url);
      return;
    }

    await serveStatic(response, url.pathname === "/" ? "/index.html" : url.pathname);
  } catch (error) {
    sendJson(response, 500, {
      error: "Internal server error",
      detail: error.message,
    });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Agent Sprint running on http://${HOST}:${PORT}`);
  console.log(`Storage mode: ${getStorageLabel()}`);
});

async function handleApi(request, response, url) {
  if (request.method === "GET" && url.pathname === "/api/health") {
    sendJson(response, 200, {
      status: "ok",
      storage: getStorageLabel(),
    });
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/runs") {
    const runs = await store.list();
    sendJson(response, 200, { runs });
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/runs") {
    const body = await readJson(request);
    const prompt = String(body.prompt || "").trim();
    const user = String(body.user || "demo-user").trim();

    if (!prompt) {
      sendJson(response, 400, { error: "Prompt is required." });
      return;
    }

    const timestamp = new Date().toISOString();
    const run = {
      id: randomUUID(),
      user,
      prompt,
      status: "queued",
      result: null,
      error: null,
      createdAt: timestamp,
      updatedAt: timestamp,
    };

    await store.create(run);
    void executeRun(run.id);
    sendJson(response, 201, { run });
    return;
  }

  if (request.method === "GET" && url.pathname.startsWith("/api/runs/")) {
    const id = url.pathname.split("/").pop();
    const run = await store.get(id);

    if (!run) {
      sendJson(response, 404, { error: "Run not found." });
      return;
    }

    sendJson(response, 200, { run });
    return;
  }

  sendJson(response, 404, { error: "Not found." });
}

async function executeRun(id) {
  const run = await store.get(id);
  if (!run) {
    return;
  }

  await store.update(id, {
    status: "running",
    updatedAt: new Date().toISOString(),
  });

  try {
    await delay(1200);
    const result = buildMockResult(run.prompt, run.user);
    await store.update(id, {
      status: "completed",
      result,
      updatedAt: new Date().toISOString(),
    });
  } catch (error) {
    await store.update(id, {
      status: "failed",
      error: error.message,
      updatedAt: new Date().toISOString(),
    });
  }
}

function buildMockResult(prompt, user) {
  const words = prompt
    .split(/\s+/)
    .map((word) => word.replace(/[^\p{L}\p{N}-]/gu, ""))
    .filter(Boolean);

  const keywords = [...new Set(words)].slice(0, 3);
  const keywordLabel = keywords.length > 0 ? keywords.join(", ") : "your idea";

  return {
    title: `Plan for ${user}`,
    summary: `This mock agent run turned "${prompt}" into a simple execution brief you can demo immediately.`,
    bullets: [
      `Focus the MVP on ${keywordLabel}.`,
      "Keep one happy-path user flow and store run results in Supabase later if needed.",
      "Use the current backend API as the single place that starts and tracks agent jobs.",
    ],
  };
}

function createStore() {
  if (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return new SupabaseRunStore({
      url: process.env.SUPABASE_URL,
      key: process.env.SUPABASE_SERVICE_ROLE_KEY,
      table: process.env.SUPABASE_RUNS_TABLE || "agent_runs",
    });
  }

  return new InMemoryRunStore();
}

function getStorageLabel() {
  return store instanceof SupabaseRunStore ? "Supabase" : "In-memory";
}

function serializeRun(run) {
  return {
    id: run.id,
    user_name: run.user,
    prompt: run.prompt,
    status: run.status,
    result: run.result,
    error: run.error,
    created_at: run.createdAt,
    updated_at: run.updatedAt,
  };
}

function deserializeRun(row) {
  return {
    id: row.id,
    user: row.user_name,
    prompt: row.prompt,
    status: row.status,
    result: row.result,
    error: row.error,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

async function serveStatic(response, pathname) {
  const normalizedPath = normalize(pathname).replace(/^(\.\.[/\\])+/, "");
  const filePath = join(PUBLIC_ROOT, normalizedPath);
  const extension = extname(filePath);

  try {
    const content = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": MIME_TYPES[extension] || "application/octet-stream",
    });
    response.end(content);
  } catch (error) {
    sendJson(response, 404, { error: "File not found." });
  }
}

async function readJson(request) {
  const chunks = [];

  for await (const chunk of request) {
    chunks.push(chunk);
  }

  const rawBody = Buffer.concat(chunks).toString("utf-8");
  return rawBody ? JSON.parse(rawBody) : {};
}

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
  });
  response.end(JSON.stringify(payload));
}

function delay(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}
