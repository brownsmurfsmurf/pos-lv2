// BFF（設計仕様書 7.5 BFF-1〜4、SEC-02/04）。サーバ側でのみ実行される。
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";
import type { ZodType } from "zod";
import { LIMITS } from "./limits";
import { ERROR_MESSAGES } from "./errors";

export const COOKIE_NAME = "pos_token";
const UPSTREAM = process.env.API_UPSTREAM_URL ?? "http://localhost:8000";
const JSON_HEADERS = { "Content-Type": "application/json" };

export function errorResponse(status: number, code: string, details: Record<string, unknown> = {}) {
  return NextResponse.json({ error: { code, message: ERROR_MESSAGES[code] ?? code, details } }, { status });
}

/** BFF-3: 本文を Zod で検証する。不正なら 400 を返し FastAPI へ送らない。 */
export async function parseBody<T>(
  req: NextRequest,
  schema: ZodType<T>,
): Promise<{ ok: true; data: T } | { ok: false; res: NextResponse }> {
  const length = Number(req.headers.get("content-length") ?? "0");
  if (length > LIMITS.BODY_MAX_BYTES) {
    return { ok: false, res: errorResponse(400, "VALIDATION_ERROR", { reason: "body too large" }) };
  }
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    return { ok: false, res: errorResponse(400, "VALIDATION_ERROR", { reason: "invalid json" }) };
  }
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    // フィールドのパスと種別のみ返す（入力値は返さない）
    const fields = parsed.error.issues.map((i) => ({ path: i.path.map(String), code: i.code }));
    return { ok: false, res: errorResponse(400, "VALIDATION_ERROR", { fields }) };
  }
  return { ok: true, data: parsed.data };
}

export interface ForwardOptions {
  method?: "GET" | "POST";
  body?: unknown;
  auth?: boolean; // false は /auth/login のみ
}

/** BFF-1/2/4: 同じパスで FastAPI /api/v1 へ中継し、Cookie の JWT を Bearer に付け替える。5xx は正規化する。 */
export async function forward(path: string, opts: ForwardOptions = {}): Promise<NextResponse> {
  const { method = "GET", body, auth = true } = opts;
  const headers: Record<string, string> = { ...JSON_HEADERS };
  if (auth) {
    const token = (await cookies()).get(COOKIE_NAME)?.value;
    if (!token) return errorResponse(401, "AUTH_REQUIRED");
    headers.Authorization = `Bearer ${token}`;
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${UPSTREAM}/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return errorResponse(503, "SERVICE_UNAVAILABLE");
  }

  if (upstream.status >= 500) {
    // BFF-4: 内部情報を隠す
    return errorResponse(upstream.status === 503 ? 503 : 500, upstream.status === 503 ? "SERVICE_UNAVAILABLE" : "INTERNAL_ERROR");
  }

  const text = await upstream.text();
  const res = new NextResponse(text, { status: upstream.status, headers: JSON_HEADERS });
  if (auth && upstream.status === 401) {
    res.cookies.delete(COOKIE_NAME); // 期限切れ・無効なトークンは捨てる
  }
  return res;
}

/** SEC-02: HttpOnly; Secure; SameSite=Strict; Path=/ の Cookie にトークンを格納する。 */
export function setTokenCookie(res: NextResponse, token: string, maxAgeSeconds: number) {
  res.cookies.set({
    name: COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: maxAgeSeconds,
  });
}
