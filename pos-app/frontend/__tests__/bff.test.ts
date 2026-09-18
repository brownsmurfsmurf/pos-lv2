/** @jest-environment node */
// IT-04〜06, 10, 32 の BFF 側（テスト仕様書 6.1）: Cookie ⇄ Bearer の付け替え、Zod 400、5xx の正規化
import { NextRequest } from "next/server";

const cookieStore = new Map<string, string>();
jest.mock("next/headers", () => ({
  cookies: async () => ({ get: (name: string) => (cookieStore.has(name) ? { name, value: cookieStore.get(name) } : undefined) }),
}));

import { COOKIE_NAME, forward, parseBody } from "@/lib/bff";
import { quoteRequestSchema } from "@/lib/schemas";

const fetchMock = jest.fn();
beforeEach(() => {
  cookieStore.clear();
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
});

function upstream(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("forward", () => {
  it("IT-05 Cookie のトークンを Authorization: Bearer に付け替える", async () => {
    cookieStore.set(COOKIE_NAME, "tok123");
    fetchMock.mockResolvedValue(upstream(200, { id: 1 }));
    const res = await forward("/auth/me");
    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/v1/auth/me");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok123");
  });

  it("IT-06 Cookie なしは FastAPI を呼ばず 401 AUTH_REQUIRED", async () => {
    const res = await forward("/auth/me");
    expect(res.status).toBe(401);
    expect((await res.json()).error.code).toBe("AUTH_REQUIRED");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("IT-06b 上流 401 なら Cookie を削除する", async () => {
    cookieStore.set(COOKIE_NAME, "expired");
    fetchMock.mockResolvedValue(upstream(401, { error: { code: "AUTH_REQUIRED", message: "", details: {} } }));
    const res = await forward("/auth/me");
    expect(res.status).toBe(401);
    expect(res.cookies.get(COOKIE_NAME)?.value).toBe("");
  });

  it("IT-32 上流 500 は INTERNAL_ERROR に置き換え、内部情報を含まない", async () => {
    cookieStore.set(COOKIE_NAME, "tok");
    fetchMock.mockResolvedValue(upstream(500, { detail: "Traceback: secret sql" }));
    const res = await forward("/products/4901234567894");
    expect(res.status).toBe(500);
    const text = await res.text();
    expect(text).toContain("INTERNAL_ERROR");
    expect(text).not.toContain("secret");
  });

  it("上流に届かないときは 503 SERVICE_UNAVAILABLE", async () => {
    cookieStore.set(COOKIE_NAME, "tok");
    fetchMock.mockRejectedValue(new Error("ECONNREFUSED"));
    const res = await forward("/auth/me");
    expect(res.status).toBe(503);
  });
});

describe("parseBody", () => {
  const mk = (body: unknown) =>
    new NextRequest("http://localhost/api/pricing/quote", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    });

  it("IT-10 型・形式が不正なら 400 で FastAPI へ送らない", async () => {
    const r = await parseBody(mk({ member_code: null, items: [{ product_code: "49012345678AB", quantity: 1 }] }), quoteRequestSchema);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.res.status).toBe(400);
      const body = await r.res.json();
      expect(body.error.code).toBe("VALIDATION_ERROR");
      expect(JSON.stringify(body)).not.toContain("49012345678AB"); // 入力値は返さない
    }
  });

  it("正常な本文は data を返す", async () => {
    const r = await parseBody(mk({ member_code: "M0001", items: [{ product_code: "4901234567894", quantity: 2 }] }), quoteRequestSchema);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.data.items[0].quantity).toBe(2);
  });

  it("JSON でない本文は 400", async () => {
    const req = new NextRequest("http://localhost/api/pricing/quote", { method: "POST", body: "not json" });
    const r = await parseBody(req, quoteRequestSchema);
    expect(r.ok).toBe(false);
  });
});
