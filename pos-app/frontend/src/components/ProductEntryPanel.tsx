"use client";
// SC-02-08〜13 商品コード入力欄／読み込み／名称／単価／追加／「1 件追加」表示（FR-03-3〜6、FR-04-1/2）
import { useState } from "react";
import { LIMITS } from "@/lib/limits";
import { formatYen } from "@/lib/pricing";
import type { ProductInfo } from "@/lib/types";

interface Props {
  pendingProduct: ProductInfo | null;
  addedFlash: boolean; // SC-02-13
  onRead: (code: string) => void;
  onAdd: () => void;
}

export function ProductEntryPanel({ pendingProduct, addedFlash, onRead, onAdd }: Props) {
  const [code, setCode] = useState("");
  const read = () => {
    if (!code) return;
    onRead(code);
    setCode("");
  };
  return (
    <section className="panel" aria-labelledby="product-heading">
      <h2 id="product-heading" className="panel__title">商品</h2>
      <div className="row">
        <input
          className="input"
          aria-label="商品コード"
          placeholder="商品コード（手入力）"
          inputMode="numeric"
          value={code}
          maxLength={LIMITS.PRODUCT_CODE_MAX}
          onChange={(e) => setCode(e.target.value.replace(/\s/g, ""))}
          onKeyDown={(e) => e.key === "Enter" && read()}
        />
        <button type="button" className="btn" onClick={read}>
          商品コード読み込み
        </button>
      </div>
      <div className="row">
        <div className="field" data-testid="pending-name">
          名称: <strong>{pendingProduct?.name ?? ""}</strong>
        </div>
        <div className="field" data-testid="pending-price">
          単価: <strong>{pendingProduct ? formatYen(pendingProduct.unit_price) : ""}</strong>
        </div>
        <button type="button" className="btn btn--primary" disabled={!pendingProduct} onClick={onAdd}>
          追加
        </button>
        {addedFlash && (
          <span className="added" role="status" data-testid="added-indicator">
            1 件追加しました
          </span>
        )}
      </div>
    </section>
  );
}
