// SC-02-19 合計金額（FR-05-8、FR-07-1）。値は API-05 の結果をそのまま表示する
import { formatYen } from "@/lib/pricing";
import type { QuoteResult } from "@/lib/types";

export function TotalsPanel({ quote }: { quote: QuoteResult | null }) {
  const sub = quote?.subtotal_excl_tax ?? 0;
  const tax = quote?.tax_amount ?? 0;
  const total = quote?.total_incl_tax ?? 0;
  return (
    <section className="panel totals" aria-labelledby="totals-heading" data-testid="totals">
      <h2 id="totals-heading" className="panel__title">合計</h2>
      <div className="totals__row">
        <span>税抜合計</span>
        <span data-testid="subtotal">{formatYen(sub)}</span>
      </div>
      <div className="totals__row">
        <span>消費税{quote ? `（${quote.tax_rate}%）` : ""}</span>
        <span data-testid="tax">{formatYen(tax)}</span>
      </div>
      <div className="totals__row totals__row--grand">
        <span>税込合計</span>
        <span data-testid="total">{formatYen(total)}</span>
      </div>
    </section>
  );
}
