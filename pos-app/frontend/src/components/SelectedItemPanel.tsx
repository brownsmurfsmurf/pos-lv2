"use client";
// SC-02-16〜18 選択商品の情報／数量変更／削除（FR-05-3〜8）。数量は直接入力と ± の両方（Q-1 は未決。★ 仮置き）
import { LIMITS } from "@/lib/limits";
import type { CartLine } from "@/features/cart/store";
import { formatYen } from "@/lib/pricing";
import type { ProductInfo, QuoteLine } from "@/lib/types";

interface Props {
  line: CartLine | null;
  product: ProductInfo | null;
  quoteLine: QuoteLine | null;
  onChangeQuantity: (quantity: number) => void;
  onRemove: () => void;
}

export function SelectedItemPanel({ line, product, quoteLine, onChangeQuantity, onRemove }: Props) {
  if (!line) {
    return (
      <section className="panel panel--muted" aria-labelledby="selected-heading">
        <h2 id="selected-heading" className="panel__title">選択中の商品</h2>
        <p className="hint">購入リストの行を選ぶと、数量の変更と削除ができます</p>
      </section>
    );
  }
  const name = quoteLine?.product_name ?? product?.name ?? line.product_code;
  const unit = quoteLine?.unit_price ?? product?.unit_price ?? 0;
  return (
    <section className="panel" aria-labelledby="selected-heading" data-testid="selected-panel">
      <h2 id="selected-heading" className="panel__title">選択中の商品</h2>
      <div className="field">名称: <strong>{name}</strong></div>
      <div className="field">単価: <strong>{formatYen(unit)}</strong></div>
      <div className="row">
        <label className="field">
          数量:
          <button type="button" className="btn btn--small" aria-label="数量を減らす" onClick={() => onChangeQuantity(line.quantity - 1)}>
            −
          </button>
          <input
            className="input input--qty"
            type="number"
            aria-label="数量"
            min={LIMITS.QTY_MIN}
            max={LIMITS.QTY_MAX}
            value={line.quantity}
            onChange={(e) => onChangeQuantity(Number(e.target.value))}
          />
          <button type="button" className="btn btn--small" aria-label="数量を増やす" onClick={() => onChangeQuantity(line.quantity + 1)}>
            ＋
          </button>
        </label>
        <button type="button" className="btn btn--danger" onClick={onRemove}>
          削除
        </button>
      </div>
      {quoteLine?.discount && (
        <div className="field">値引き: <strong>−{formatYen(quoteLine.discount.amount)}</strong></div>
      )}
    </section>
  );
}
