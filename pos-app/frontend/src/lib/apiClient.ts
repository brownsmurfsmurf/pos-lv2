// ブラウザ → BFF（/api/*）のクライアント。FastAPI の URL は知らない（API-P1）
import { ApiError, messageFor } from "./errors";
import type {
  ApiErrorBody, CommitRequest, CommitResponse, LoginRequest, LoginResponse, MemberInfo, ProductInfo,
  QuoteRequest, QuoteResult, StaffInfo,
} from "./types";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    cache: "no-store",
  });
  if (res.ok) {
    return (await res.json()) as T;
  }
  let body: ApiErrorBody | null = null;
  try {
    body = (await res.json()) as ApiErrorBody;
  } catch {
    body = null;
  }
  const code = body?.error?.code ?? (res.status >= 500 ? "INTERNAL_ERROR" : "VALIDATION_ERROR");
  throw new ApiError(res.status, code, messageFor(code, body?.error?.message), body?.error?.details ?? {});
}

export const api = {
  login: (body: LoginRequest) => request<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<StaffInfo>("/auth/me"),
  getProduct: (code: string) => request<ProductInfo>(`/products/${encodeURIComponent(code)}`),
  getMember: (code: string) => request<MemberInfo>(`/members/${encodeURIComponent(code)}`),
  quote: (body: QuoteRequest) => request<QuoteResult>("/pricing/quote", { method: "POST", body: JSON.stringify(body) }),
  commit: (body: CommitRequest) => request<CommitResponse>("/transactions", { method: "POST", body: JSON.stringify(body) }),
};
