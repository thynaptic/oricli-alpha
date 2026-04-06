import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium, type Browser, type BrowserContext, type Page } from "playwright";

import type {
  BrowserActionRequest,
  BrowserActionResult,
  BrowserCreateSessionRequest,
  BrowserLoadStateRequest,
  BrowserOpenRequest,
  BrowserSnapshot,
  BrowserSnapshotElement,
  BrowserStateRequest,
} from "./types.js";

type Session = {
  browser: Browser;
  context: BrowserContext;
  page: Page;
  refs: Map<string, string>;
  refVersion: number;
};

const host = process.env.BROWSERD_HOST ?? "127.0.0.1";
const port = Number.parseInt(process.env.BROWSERD_PORT ?? "7791", 10);
const apiKey = process.env.BROWSER_SERVICE_API_KEY ?? "";
const sessions = new Map<string, Session>();
const stateDir = path.resolve(process.cwd(), ".state");

const snapshotScript = `
(() => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const selectorFor = (el) => {
    if (el.id) return "#" + CSS.escape(el.id);
    const parts = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
      const tag = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (!parent) {
        parts.unshift(tag);
        break;
      }
      const siblings = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
      const index = siblings.indexOf(node) + 1;
      parts.unshift(tag + ":nth-of-type(" + index + ")");
      node = parent;
    }
    return parts.join(" > ");
  };

  const nodes = Array.from(
    document.querySelectorAll('a,button,input,textarea,select,[role="button"],[tabindex]')
  );

  return nodes.map((el) => ({
    tag: el.tagName.toLowerCase(),
    role: el.getAttribute("role") || "",
    text: (el.innerText || el.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 240),
    selector: selectorFor(el),
    href: el instanceof HTMLAnchorElement ? el.href : undefined,
    inputType: el instanceof HTMLInputElement ? el.type : undefined,
    placeholder: "placeholder" in el ? (el.getAttribute("placeholder") || undefined) : undefined,
    enabled: !("disabled" in el) || !(el).disabled,
    visible: visible(el),
  }));
})();
`;

function randomID(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function sanitizeStateName(name: string): string {
  const sanitized = name.trim().replace(/[^a-zA-Z0-9_-]+/g, "_");
  if (sanitized === "") {
    throw new Error("invalid state name");
  }
  return sanitized;
}

async function parseBody<T>(req: IncomingMessage): Promise<T> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? (JSON.parse(raw) as T) : ({} as T);
}

function writeJSON(res: ServerResponse, status: number, payload: unknown): void {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(payload));
}

function getSession(sessionID: string): Session {
  const session = sessions.get(sessionID);
  if (!session) {
    throw new Error(`unknown session: ${sessionID}`);
  }
  return session;
}

async function createSnapshot(session: Session): Promise<BrowserSnapshot> {
  const rawElements = (await session.page.evaluate(snapshotScript)) as Omit<BrowserSnapshotElement, "ref">[];
  session.refs.clear();

  const elements = rawElements.map((element, index) => {
    const ref = `@e${index + 1}`;
    session.refs.set(ref, element.selector);
    return { ...element, ref };
  });

  session.refVersion += 1;

  return {
    url: session.page.url(),
    title: await session.page.title(),
    capturedAt: new Date().toISOString(),
    elements,
  };
}

function resolveLocator(session: Session, ref?: string, selector?: string) {
  const resolved = ref ? session.refs.get(ref) : selector;
  if (!resolved) {
    throw new Error("missing selector or stale ref");
  }
  return session.page.locator(resolved).first();
}

function actionTextQuery(input: BrowserActionRequest): string | undefined {
  return input.textQuery ?? (input as BrowserActionRequest & { text_query?: string }).text_query;
}

function actionURLPattern(input: BrowserActionRequest): string | undefined {
  return input.urlPattern ?? (input as BrowserActionRequest & { url_pattern?: string }).url_pattern;
}

function resolveSemanticLocator(session: Session, input: BrowserActionRequest) {
  if (input.ref || input.selector) {
    return resolveLocator(session, input.ref, input.selector);
  }
  if (input.label) {
    return session.page.getByLabel(input.label, { exact: false }).first();
  }
  if (input.role) {
    return session.page.getByRole(input.role as Parameters<Page["getByRole"]>[0], {
      name: input.name ?? actionTextQuery(input),
    }).first();
  }
  if (actionTextQuery(input)) {
    return session.page.getByText(actionTextQuery(input)!, { exact: false }).first();
  }
  if (input.name) {
    return session.page.getByRole("button", { name: input.name }).first();
  }
  throw new Error("missing selector, ref, or semantic target");
}

async function handleAction(session: Session, input: BrowserActionRequest): Promise<BrowserActionResult> {
  const timeout = input.timeoutMs ?? 10_000;
  switch (input.action) {
    case "click":
      await resolveSemanticLocator(session, input).click({ timeout });
      break;
    case "fill":
      await resolveSemanticLocator(session, input).fill(input.text ?? "", { timeout });
      break;
    case "press":
      if (input.ref || input.selector) {
        await resolveLocator(session, input.ref, input.selector).press(input.key ?? "Enter", { timeout });
      } else if (input.label || input.role || input.textQuery || input.name) {
        await resolveSemanticLocator(session, input).press(input.key ?? "Enter", { timeout });
      } else {
        await session.page.keyboard.press(input.key ?? "Enter");
      }
      break;
    case "wait_for":
      if (actionURLPattern(input)) {
        await session.page.waitForURL(actionURLPattern(input)!, { timeout });
      } else if (input.selector || input.ref || input.label || input.role || input.textQuery || input.name) {
        await resolveSemanticLocator(session, input).waitFor({ timeout });
      } else {
        await session.page.waitForLoadState("networkidle", { timeout });
      }
      break;
    case "get_text": {
      const value = await resolveSemanticLocator(session, input).innerText({ timeout });
      return {
        ok: true,
        action: input.action,
        url: session.page.url(),
        title: await session.page.title(),
        value,
      };
    }
    default:
      throw new Error(`unsupported action: ${String(input.action)}`);
  }

  return {
    ok: true,
    action: input.action,
    url: session.page.url(),
    title: await session.page.title(),
    snapshot: await createSnapshot(session),
  };
}

const server = createServer(async (req, res) => {
  try {
    if (apiKey !== "" && req.headers.authorization !== `Bearer ${apiKey}`) {
      writeJSON(res, 401, { ok: false, error: "unauthorized" });
      return;
    }

    const method = req.method ?? "GET";
    const url = new URL(req.url ?? "/", `http://${host}:${port}`);
    const parts = url.pathname.split("/").filter(Boolean);

    if (method === "GET" && url.pathname === "/health") {
      writeJSON(res, 200, { ok: true, sessions: sessions.size });
      return;
    }

    if (method === "POST" && url.pathname === "/sessions") {
      const body = await parseBody<BrowserCreateSessionRequest>(req);
      const browser = await chromium.launch({ headless: body.headless ?? true });
      const context = await browser.newContext({
        viewport: {
          width: body.viewport?.width ?? 1440,
          height: body.viewport?.height ?? 900,
        },
      });
      const page = await context.newPage();
      const sessionID = randomID("sess");
      sessions.set(sessionID, { browser, context, page, refs: new Map(), refVersion: 0 });
      writeJSON(res, 200, { ok: true, session_id: sessionID });
      return;
    }

    if (parts[0] === "sessions" && parts[1]) {
      const session = getSession(parts[1]);

      if (method === "DELETE" && parts.length === 2) {
        await session.context.close();
        await session.browser.close();
        sessions.delete(parts[1]);
        writeJSON(res, 200, { ok: true });
        return;
      }

      if (method === "POST" && parts[2] === "open") {
        const body = await parseBody<BrowserOpenRequest>(req);
        await session.page.goto(body.url, { waitUntil: body.waitUntil ?? "networkidle" });
        writeJSON(res, 200, {
          ok: true,
          url: session.page.url(),
          title: await session.page.title(),
          snapshot: await createSnapshot(session),
        });
        return;
      }

      if (method === "GET" && parts[2] === "snapshot") {
        writeJSON(res, 200, { ok: true, snapshot: await createSnapshot(session) });
        return;
      }

      if (method === "POST" && parts[2] === "action") {
        const body = await parseBody<BrowserActionRequest>(req);
        writeJSON(res, 200, await handleAction(session, body));
        return;
      }

      if (method === "POST" && parts[2] === "screenshot") {
        const outputDir = path.resolve(process.cwd(), ".playwright");
        await mkdir(outputDir, { recursive: true });
        const screenshotPath = path.join(outputDir, `${parts[1]}-${Date.now()}.png`);
        await session.page.screenshot({ path: screenshotPath, fullPage: url.searchParams.get("full") === "true" });
        writeJSON(res, 200, {
          ok: true,
          path: screenshotPath,
          url: session.page.url(),
          title: await session.page.title(),
        });
        return;
      }

      if (method === "POST" && parts[2] === "state" && parts[3] === "save") {
        const body = await parseBody<BrowserStateRequest>(req);
        const stateName = sanitizeStateName(body.stateName);
        await mkdir(stateDir, { recursive: true });
        const statePath = path.join(stateDir, `${stateName}.json`);
        await session.context.storageState({ path: statePath });
        writeJSON(res, 200, { ok: true, state_name: stateName, path: statePath });
        return;
      }
    }

    if (method === "POST" && url.pathname === "/state/load") {
      const body = await parseBody<BrowserLoadStateRequest>(req);
      const stateName = sanitizeStateName(body.stateName);
      const statePath = path.join(stateDir, `${stateName}.json`);
      const browser = await chromium.launch({ headless: body.headless ?? true });
      const context = await browser.newContext({
        viewport: {
          width: body.viewport?.width ?? 1440,
          height: body.viewport?.height ?? 900,
        },
        storageState: statePath,
      });
      const page = await context.newPage();
      const sessionID = randomID("sess");
      sessions.set(sessionID, { browser, context, page, refs: new Map(), refVersion: 0 });
      writeJSON(res, 200, { ok: true, session_id: sessionID, state_name: stateName });
      return;
    }

    writeJSON(res, 404, { ok: false, error: "not found" });
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown error";
    writeJSON(res, 500, { ok: false, error: message });
  }
});

server.listen(port, host, () => {
  console.log(`[browserd] listening on http://${host}:${port}`);
});
