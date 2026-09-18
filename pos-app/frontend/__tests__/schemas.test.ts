// UT-F-19〜25（テスト仕様書 5.2）: lib/schemas.ts の型・形式チェック
import { commitRequestSchema, memberCodeSchema, productCodeSchema, quoteRequestSchema } from "@/lib/schemas";

describe("productCodeSchema", () => {
  it("UT-F-19 13 桁の数字は通る ★", () => {
    expect(productCodeSchema.safeParse("4901234567894").success).toBe(true);
    expect(productCodeSchema.safeParse("1").success).toBe(true);
  });
  it.each([
    ["14 桁", "49012345678941"],
    ["英字混じり", "49012345678AB"],
    ["空", ""],
    ["全角数字", "４９０１２３４５６７８９４"],
    ["SQL 断片", "' OR '1'='1"],
  ])("UT-F-20〜22 %s は弾く", (_label, v) => {
    expect(productCodeSchema.safeParse(v).success).toBe(false);
  });
});

describe("memberCodeSchema", () => {
  it("UT-F-23 1・32 文字は通り 33 文字・記号は弾く ★", () => {
    expect(memberCodeSchema.safeParse("M").success).toBe(true);
    expect(memberCodeSchema.safeParse("A".repeat(32)).success).toBe(true);
    expect(memberCodeSchema.safeParse("A".repeat(33)).success).toBe(false);
    expect(memberCodeSchema.safeParse("M-0001").success).toBe(false);
  });
});

describe("quoteRequestSchema", () => {
  const ok = { member_code: null, items: [{ product_code: "4901234567894", quantity: 1 }] };
  it("UT-F-24 正常な本文は通る（会員なし null 可）", () => {
    expect(quoteRequestSchema.safeParse(ok).success).toBe(true);
    expect(quoteRequestSchema.safeParse({ ...ok, member_code: "M0001" }).success).toBe(true);
  });
  it.each([["文字列", "2"], ["小数", 1.5], ["真偽値", true], ["null", null]])(
    "UT-F-25 数量 %s は弾く（暗黙変換しない）",
    (_label, q) => {
      expect(quoteRequestSchema.safeParse({ ...ok, items: [{ product_code: "4901234567894", quantity: q }] }).success).toBe(false);
    },
  );
  it("数量 0・100 は型としては通る（業務範囲は Backend が 422）", () => {
    expect(quoteRequestSchema.safeParse({ ...ok, items: [{ product_code: "4901234567894", quantity: 0 }] }).success).toBe(true);
  });
  it("未知のキー・101 行は弾く", () => {
    expect(quoteRequestSchema.safeParse({ ...ok, extra: 1 }).success).toBe(false);
    const items = Array.from({ length: 101 }, (_, i) => ({ product_code: String(4900000000000 + i), quantity: 1 }));
    expect(quoteRequestSchema.safeParse({ member_code: null, items }).success).toBe(false);
  });
});

describe("commitRequestSchema", () => {
  it("金額は非負の整数、税率は 0〜100", () => {
    const base = {
      member_code: null,
      items: [{ product_code: "4901234567894", quantity: 1, unit_price: 150, discount_amount: 0, line_total: 150 }],
      tax_rate: 10, subtotal_excl_tax: 150, tax_amount: 15, total_incl_tax: 165,
    };
    expect(commitRequestSchema.safeParse(base).success).toBe(true);
    expect(commitRequestSchema.safeParse({ ...base, total_incl_tax: 165.5 }).success).toBe(false);
    expect(commitRequestSchema.safeParse({ ...base, tax_rate: 101 }).success).toBe(false);
    expect(commitRequestSchema.safeParse({ ...base, items: [{ ...base.items[0], unit_price: -1 }] }).success).toBe(false);
  });
});
