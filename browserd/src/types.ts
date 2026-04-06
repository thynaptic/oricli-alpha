export type BrowserActionName =
  | "click"
  | "fill"
  | "press"
  | "wait_for"
  | "get_text";

export interface BrowserCreateSessionRequest {
  headless?: boolean;
  viewport?: {
    width?: number;
    height?: number;
  };
}

export interface BrowserOpenRequest {
  url: string;
  waitUntil?: "load" | "domcontentloaded" | "networkidle" | "commit";
}

export interface BrowserActionRequest {
  action: BrowserActionName;
  ref?: string;
  selector?: string;
  text?: string;
  textQuery?: string;
  label?: string;
  role?: string;
  name?: string;
  urlPattern?: string;
  key?: string;
  timeoutMs?: number;
}

export interface BrowserSnapshotElement {
  ref: string;
  tag: string;
  role: string;
  text: string;
  selector: string;
  href?: string;
  inputType?: string;
  placeholder?: string;
  enabled: boolean;
  visible: boolean;
}

export interface BrowserSnapshot {
  url: string;
  title: string;
  capturedAt: string;
  elements: BrowserSnapshotElement[];
}

export interface BrowserActionResult {
  ok: boolean;
  action: BrowserActionName;
  url: string;
  title: string;
  value?: string;
  snapshot?: BrowserSnapshot;
}

export interface BrowserStateRequest {
  stateName: string;
}

export interface BrowserLoadStateRequest extends BrowserStateRequest {
  headless?: boolean;
  viewport?: {
    width?: number;
    height?: number;
  };
}
