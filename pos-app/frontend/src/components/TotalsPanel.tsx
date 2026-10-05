// 合計（FR-05-8、FR-07-1）。★ 税抜合計と税込合計を表示する（K-25）。値は API-05 の結果をそのまま出す
import { formatYen } from "@/lib/pricing";
import type { QuoteResult } from "@/lib/types";

export function TotalsPanel({ quote }: { quote: QuoteResult | null }) {
  return (
    <section className="panel totals" aria-labelledby="totals-heading" data-testid="totals">
      <h2 id="totals-heading" className="panel__title">合計</h2>
      <div className="totals__row">
        <span>税抜合計</span>
        <span data-testid="subtotal">{formatYen(quote?.subtotal_excl_tax ?? 0)}</span>
      </div>
      <div className="totals__row totals__row--grand">
        <span>税込合計</span>
        <span data-testid="total">{formatYen(quote?.total_incl_tax ?? 0)}</span>
      </div>
    </section>
  );
}
