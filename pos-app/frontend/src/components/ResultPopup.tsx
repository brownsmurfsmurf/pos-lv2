// SC-02-21 購入確定ポップアップ（FR-08-3、FR-07-1）。閉じると画面を空にする（FR-08-4）
import { formatYen } from "@/lib/pricing";
import type { CommitResponse } from "@/lib/types";

export function ResultPopup({ result, onClose }: { result: CommitResponse | null; onClose: () => void }) {
  if (!result) return null;
  return (
    <div className="popup-backdrop" role="presentation">
      <div className="popup" role="dialog" aria-modal="true" aria-labelledby="popup-title" data-testid="result-popup">
        <h2 id="popup-title">購入が完了しました</h2>
        <div className="totals__row">
          <span>税抜合計</span>
          <span data-testid="popup-subtotal">{formatYen(result.subtotal_excl_tax)}</span>
        </div>
        <div className="totals__row">
          <span>消費税</span>
          <span>{formatYen(result.tax_amount)}</span>
        </div>
        <div className="totals__row totals__row--grand">
          <span>税込合計</span>
          <span data-testid="popup-total">{formatYen(result.total_incl_tax)}</span>
        </div>
        <p className="hint">取引番号: {result.transaction_id}</p>
        <button type="button" className="btn btn--primary" onClick={onClose} autoFocus>
          閉じる
        </button>
      </div>
    </div>
  );
}
