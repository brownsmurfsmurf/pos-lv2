// 単体テスト UT-F-15, UT-F-16, UT-F-27（テスト仕様書 v2 の 4.2）: 入力の形と、連続読み取りの判定
import { createScanGate } from "@/features/scanner/debounce";
import { ERROR_MESSAGES, ApiError, messageFor } from "@/lib/errors";
import { commitRequestSchema, memberCodeSchema, productCodeSchema, quoteRequestSchema } from "@/lib/schemas";

describe("UT-F-15 ★ 商品コードの形 (K-21)", () => {
  it.each([["1 桁", "4"], ["13 桁", "4901234567894"]])("%s は通る", (_l, v) => {
    expect(productCodeSchema.safeParse(v).success).toBe(true);
  });
  it.each([["14 桁", "49012345678941"], ["全角数字", "４９０１２３４５６７８９４"], ["空", ""], ["英字まじり", "49012345678AB"]])(
    "%s は通らない",
    (_l, v) => {
      expect(productCodeSchema.safeParse(v).success).toBe(false);
    },
  );
});

describe("UT-F-16 数量の型 (課題: 入力の上下限、エラー処理)", () => {
  const ok = { member_code: null, items: [{ product_code: "4901234567894", quantity: 1 }] };
  it.each([["小数", 1.5], ["null", null], ["数字でない文字列", "abc"]])("数量 %s は通らない", (_l, q) => {
    expect(quoteRequestSchema.safeParse({ ...ok, items: [{ product_code: "4901234567894", quantity: q }] }).success).toBe(false);
  });
  it("整数は通る。0 や 100 は形としては通る（範囲はサーバが 422 で判定する）", () => {
    expect(quoteRequestSchema.safeParse(ok).success).toBe(true);
    expect(quoteRequestSchema.safeParse({ ...ok, items: [{ product_code: "4901234567894", quantity: 100 }] }).success).toBe(true);
  });
});

describe("UT-F-27 ★ 同じバーコードの連続読み取り (FR-03-2, K-34)", () => {
  it("1,500 ミリ秒後は無視、1,501 ミリ秒後は受け付ける", () => {
    const gate = createScanGate(1500);
    expect(gate.accept("4901234567894", 10_000)).toBe(true); // 1 回目
    expect(gate.accept("4901234567894", 11_500)).toBe(false); // ちょうど 1.5 秒後（以内）→ 無視
    expect(gate.accept("4901234567894", 11_501)).toBe(true); // 1.5 秒を超えた → 受け付ける
  });
  it("別のコードはすぐに受け付ける", () => {
    const gate = createScanGate(1500);
    expect(gate.accept("4901234567894", 0)).toBe(true);
    expect(gate.accept("4901234567900", 1)).toBe(true);
    expect(gate.accept("4901234567894", 2)).toBe(true);
  });
});

describe("補助: 会員ID・確定の入力・文言", () => {
  it("会員ID は英数字 1〜32 文字 ★ (K-21)", () => {
    expect(memberCodeSchema.safeParse("M").success).toBe(true);
    expect(memberCodeSchema.safeParse("A".repeat(32)).success).toBe(true);
    expect(memberCodeSchema.safeParse("A".repeat(33)).success).toBe(false);
    expect(memberCodeSchema.safeParse("M-0001").success).toBe(false);
    expect(memberCodeSchema.safeParse("").success).toBe(false);
  });
  it("見積の入力: 会員なしは null。知らない項目と 101 行は通らない ★ (K-32)", () => {
    expect(quoteRequestSchema.safeParse({ member_code: null, items: [] }).success).toBe(true);
    expect(quoteRequestSchema.safeParse({ member_code: null, items: [], extra: 1 }).success).toBe(false);
    const items = Array.from({ length: 101 }, (_, i) => ({ product_code: String(4900000000000 + i), quantity: 1 }));
    expect(quoteRequestSchema.safeParse({ member_code: null, items }).success).toBe(false);
  });
  it("同じ商品コードが 2 行あれば通らない ★ (K-32)", () => {
    const dup = [{ product_code: "4901234567894", quantity: 1 }, { product_code: "4901234567894", quantity: 2 }];
    expect(quoteRequestSchema.safeParse({ member_code: null, items: dup }).success).toBe(false);
  });
  it("確定の入力: 金額は 0 以上の整数、税率は 0〜100", () => {
    const base = {
      member_code: null,
      items: [{ product_code: "4901234567894", quantity: 2, unit_price: 150, discount_amount: 60, line_total: 240 }],
      tax_rate: 10, subtotal_excl_tax: 240, tax_amount: 24, total_incl_tax: 264,
    };
    expect(commitRequestSchema.safeParse(base).success).toBe(true);
    expect(commitRequestSchema.safeParse({ ...base, total_incl_tax: 264.5 }).success).toBe(false);
    expect(commitRequestSchema.safeParse({ ...base, tax_rate: 101 }).success).toBe(false);
  });
  it("文言: 要求一覧の文言をそのまま使う (FR-03-5)。知らない code は既定の文言", () => {
    expect(messageFor("PRODUCT_NOT_FOUND")).toBe("商品がマスタ未登録です");
    expect(messageFor("UNKNOWN", "サーバの文言")).toBe("サーバの文言");
    expect(messageFor("UNKNOWN")).toBe(ERROR_MESSAGES.INTERNAL_ERROR);
    const e = new ApiError(409, "PRICE_MISMATCH", messageFor("PRICE_MISMATCH"), { server: {} });
    expect(e.status).toBe(409);
    expect(e.details).toEqual({ server: {} });
  });
});
