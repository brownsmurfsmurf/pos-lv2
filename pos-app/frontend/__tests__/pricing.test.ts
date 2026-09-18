// UT-F-01〜05（テスト仕様書 5.2）: lib/pricing.ts の再集計
import { aggregateTotals } from "@/lib/pricing";

describe("aggregateTotals", () => {
  it("UT-F-01 図1 の 4 行（270+188+480+160、税率 10）→ 税抜 1,098・税込 1,207 ★", () => {
    const lines = [{ line_total: 270 }, { line_total: 188 }, { line_total: 480 }, { line_total: 160 }];
    expect(aggregateTotals(lines, 10)).toEqual({ subtotal_excl_tax: 1098, tax_amount: 109, total_incl_tax: 1207 });
  });

  it("UT-F-02 0 行 → 0", () => {
    expect(aggregateTotals([], 10)).toEqual({ subtotal_excl_tax: 0, tax_amount: 0, total_incl_tax: 0 });
  });

  it("UT-F-03 1 行", () => {
    expect(aggregateTotals([{ line_total: 150 }], 10)).toEqual({ subtotal_excl_tax: 150, tax_amount: 15, total_incl_tax: 165 });
  });

  it("UT-F-04 税抜 5 → 税額 0（切り捨て ★）", () => {
    expect(aggregateTotals([{ line_total: 5 }], 10).tax_amount).toBe(0);
  });

  it("UT-F-05 NaN・文字列は例外（NaN を返さない）", () => {
    expect(() => aggregateTotals([{ line_total: Number.NaN }], 10)).toThrow(TypeError);
    expect(() => aggregateTotals([{ line_total: "150" as unknown as number }], 10)).toThrow(TypeError);
    expect(() => aggregateTotals([{ line_total: 100 }], Number.NaN)).toThrow(TypeError);
  });
});
