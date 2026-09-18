// 表示用の再集計（テスト仕様書 UT-F-01〜05）。
// 値引きの判定・税率の決定は Backend の PricingService のみが行う（SEC-05）。ここは API-05 の結果を合計し直すだけ。
import type { Money, QuoteLine, Rate } from "./types";

export interface Totals { subtotal_excl_tax: Money; tax_amount: Money; total_incl_tax: Money }

function assertInteger(name: string, v: unknown): number {
  if (typeof v !== "number" || !Number.isFinite(v) || !Number.isInteger(v)) {
    throw new TypeError(`${name} は整数である必要があります`);
  }
  return v;
}

export function aggregateTotals(lines: Pick<QuoteLine, "line_total">[], taxRate: Rate): Totals {
  if (typeof taxRate !== "number" || !Number.isFinite(taxRate) || taxRate < 0 || taxRate > 100) {
    throw new TypeError("tax_rate は 0〜100 の数値である必要があります");
  }
  const subtotal = lines.reduce((acc, l) => acc + assertInteger("line_total", l.line_total), 0);
  // 端数は 1 円未満切り捨て（★ Q-6 の仮置き。Backend と同じ規則）
  const tax = Math.floor((subtotal * taxRate) / 100);
  return { subtotal_excl_tax: subtotal, tax_amount: tax, total_incl_tax: subtotal + tax };
}

export function formatYen(v: Money): string {
  return `${v.toLocaleString("ja-JP")}円`;
}
