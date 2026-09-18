// SC-02-14/15 購入リストと選択行の強調（FR-04-7、FR-06-5、FR-05-1/2）
import type { CartLine } from "@/features/cart/store";
import { formatYen } from "@/lib/pricing";
import type { ProductInfo, QuoteResult } from "@/lib/types";

interface Props {
  lines: CartLine[];
  catalog: Record<string, ProductInfo>;
  quote: QuoteResult | null;
  selectedLineNo: number | null;
  onSelect: (lineNo: number) => void;
}

export function CartTable({ lines, catalog, quote, selectedLineNo, onSelect }: Props) {
  return (
    <section className="panel" aria-labelledby="cart-heading">
      <h2 id="cart-heading" className="panel__title">購入リスト</h2>
      <table className="cart" data-testid="cart-table">
        <thead>
          <tr>
            <th>#</th>
            <th>商品名</th>
            <th className="num">数量</th>
            <th className="num">単価</th>
            <th className="num">値引き</th>
            <th className="num">小計</th>
          </tr>
        </thead>
        <tbody>
          {lines.length === 0 && (
            <tr>
              <td colSpan={6} className="cart__empty">商品が登録されていません</td>
            </tr>
          )}
          {lines.map((line, i) => {
            const lineNo = i + 1;
            const q = quote?.lines[i];
            const p = catalog[line.product_code];
            const name = q?.product_name ?? p?.name ?? line.product_code;
            const unit = q?.unit_price ?? p?.unit_price ?? 0;
            const discount = q?.discount?.amount ?? 0;
            const total = q?.line_total ?? unit * line.quantity;
            const selected = selectedLineNo === lineNo;
            return (
              <tr
                key={line.product_code}
                className={selected ? "cart__row cart__row--selected" : "cart__row"}
                aria-selected={selected}
                data-testid={`cart-row-${lineNo}`}
                onClick={() => onSelect(lineNo)}
              >
                <td>{lineNo}</td>
                <td>{name}</td>
                <td className="num">{line.quantity}</td>
                <td className="num">{formatYen(unit)}</td>
                <td className="num">{discount > 0 ? `−${formatYen(discount)}` : ""}</td>
                <td className="num">{formatYen(total)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
