"use client";
// SC-02 POS メイン画面のオーケストレーション（設計仕様書 5 章、8 章のシーケンス）
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useCartStore } from "@/features/cart/useCartStore";
import { CameraPreview } from "@/features/scanner/CameraPreview";
import { api } from "@/lib/apiClient";
import { ADDED_MESSAGE, ApiError, messageFor } from "@/lib/errors";
import type { CommitRequest, QuoteResult } from "@/lib/types";
import { CartTable } from "./CartTable";
import { MemberPanel } from "./MemberPanel";
import { MessageBar } from "./MessageBar";
import { PosHeader } from "./PosHeader";
import { ProductEntryPanel } from "./ProductEntryPanel";
import { ResultPopup } from "./ResultPopup";
import { SelectedItemPanel } from "./SelectedItemPanel";
import { TotalsPanel } from "./TotalsPanel";

export function PosScreen() {
  const router = useRouter();
  const [state, store] = useCartStore();
  const [tone, setTone] = useState<"info" | "error">("info");
  const [cameraOk, setCameraOk] = useState(true);
  const [addedFlash, setAddedFlash] = useState(false);
  const [busy, setBusy] = useState(false);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showError = useCallback(
    (err: unknown) => {
      if (err instanceof ApiError) {
        if (err.code === "AUTH_REQUIRED") {
          router.replace("/login");
          return;
        }
        setTone("error");
        store.setMessage(err.message);
      } else {
        setTone("error");
        store.setMessage(messageFor("INTERNAL_ERROR"));
      }
    },
    [router, store],
  );

  const showInfo = useCallback(
    (msg: string | null) => {
      setTone("info");
      store.setMessage(msg);
    },
    [store],
  );

  // 担当者名（SC-02-01）
  useEffect(() => {
    api.me().then(store.setStaff).catch(showError);
  }, [store, showError]);

  // 購入リストか会員が変わるたびに API-05 を呼ぶ（5.2）。金額の正本は Backend
  useEffect(() => {
    if (state.quoteRevision === 0) return;
    if (state.lines.length === 0) {
      store.setQuote(null);
      return;
    }
    let cancelled = false;
    api
      .quote({ member_code: state.member?.member_code ?? null, items: state.lines })
      .then((q) => !cancelled && store.setQuote(q))
      .catch((e) => !cancelled && showError(e));
    return () => {
      cancelled = true;
    };
    // quoteRevision は行・会員の変更でのみ増える
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.quoteRevision]);

  function flashAdded() {
    setAddedFlash(true);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setAddedFlash(false), 1500);
  }

  function addToCart(p: { id: number; product_code: string; name: string; unit_price: number }) {
    if (store.addProduct(p)) {
      showInfo(ADDED_MESSAGE);
      flashAdded();
    } else {
      setTone("error");
      store.setMessage(messageFor("QUANTITY_OUT_OF_RANGE"));
    }
  }

  // FR-03-3〜5: 手入力で読み込み → 名称・単価を表示（追加ボタンでリストへ）
  async function readProduct(code: string) {
    try {
      const p = await api.getProduct(code);
      store.setPendingProduct(p);
      showInfo(null);
    } catch (e) {
      store.setPendingProduct(null);
      showError(e);
    }
  }

  // FR-03-1/2: スキャンした商品は追加ボタンなしでリストへ（★ Q-5 の仮置き）
  async function scanProduct(code: string) {
    try {
      addToCart(await api.getProduct(code));
    } catch (e) {
      showError(e);
    }
  }

  // FR-02: 会員IDの読み込み（空なら会員なしで進む。FR-02-7）
  async function readMember(code: string) {
    if (!code) {
      store.setMember(null);
      showInfo("会員なしで進みます");
      return;
    }
    try {
      const m = await api.getMember(code);
      store.setMember(m);
      showInfo(null);
    } catch (e) {
      showError(e); // MEMBER_NOT_FOUND: 会員は未設定のまま（その後は Q-3）
    } finally {
      store.setScanMode("product");
    }
  }

  function onDetected(code: string) {
    if (state.scanMode === "member") void readMember(code);
    else void scanProduct(code);
  }

  function changeQuantity(q: number) {
    if (state.selectedLineNo === null) return;
    if (!store.setQuantity(state.selectedLineNo, q)) {
      setTone("error");
      store.setMessage(messageFor("QUANTITY_OUT_OF_RANGE")); // ★ Q-2: 断って直前の数量を維持
    } else {
      showInfo(null);
    }
  }

  // FR-08-1: 購入確定。表示していた金額を送り、Backend が再計算して照合する（SEC-05）
  async function purchase() {
    const q = state.quote;
    if (!q || state.lines.length === 0) {
      setTone("error");
      store.setMessage(messageFor("CART_EMPTY"));
      return;
    }
    const body: CommitRequest = {
      member_code: state.member?.member_code ?? null,
      items: q.lines.map((l) => ({
        product_code: l.product_code,
        quantity: l.quantity,
        unit_price: l.unit_price,
        discount_amount: l.discount?.amount ?? 0,
        line_total: l.line_total,
      })),
      tax_rate: q.tax_rate,
      subtotal_excl_tax: q.subtotal_excl_tax,
      tax_amount: q.tax_amount,
      total_incl_tax: q.total_incl_tax,
    };
    setBusy(true);
    try {
      store.commitSucceeded(await api.commit(body));
    } catch (e) {
      if (e instanceof ApiError && e.code === "PRICE_MISMATCH" && e.details.server) {
        store.setQuote(e.details.server as QuoteResult); // 表示を Backend の値に差し替え。保存はされていない
      }
      showError(e);
    } finally {
      setBusy(false);
    }
  }

  const selectedLine = state.selectedLineNo ? state.lines[state.selectedLineNo - 1] ?? null : null;
  const selectedQuote = state.selectedLineNo ? state.quote?.lines[state.selectedLineNo - 1] ?? null : null;

  return (
    <div className="pos">
      <PosHeader staff={state.staff} />
      <MessageBar message={state.message} tone={tone} />
      <div className="pos__grid">
        <div className="pos__left">
          <MemberPanel
            member={state.member}
            scanMode={state.scanMode}
            onRead={readMember}
            onStartScan={() => {
              store.setScanMode(state.scanMode === "member" ? "product" : "member");
              showInfo(state.scanMode === "member" ? null : "会員証をカメラに向けてください");
            }}
          />
          {cameraOk ? (
            <CameraPreview
              active={state.status !== "committed"}
              label={state.scanMode === "member" ? "会員証を読み取り中" : "商品バーコードを読み取り中"}
              onDetected={onDetected}
              onUnavailable={() => {
                setCameraOk(false);
                setTone("error");
                store.setMessage(messageFor("CAMERA_UNAVAILABLE"));
              }}
            />
          ) : (
            <div className="camera camera--off">カメラは使用できません（手入力をご利用ください）</div>
          )}
          <ProductEntryPanel
            pendingProduct={state.pendingProduct}
            addedFlash={addedFlash}
            onRead={readProduct}
            onAdd={() => state.pendingProduct && addToCart(state.pendingProduct)}
          />
        </div>
        <div className="pos__right">
          <CartTable
            lines={state.lines}
            catalog={state.catalog}
            quote={state.quote}
            selectedLineNo={state.selectedLineNo}
            onSelect={(n) => store.selectLine(state.selectedLineNo === n ? null : n)}
          />
          <SelectedItemPanel
            line={selectedLine}
            product={selectedLine ? state.catalog[selectedLine.product_code] ?? null : null}
            quoteLine={selectedQuote}
            onChangeQuantity={changeQuantity}
            onRemove={() => state.selectedLineNo && store.removeLine(state.selectedLineNo)}
          />
          <TotalsPanel quote={state.quote} />
          <button
            type="button"
            className="btn btn--primary btn--purchase"
            onClick={purchase}
            disabled={busy || state.lines.length === 0 || !state.quote}
            data-testid="purchase-button"
          >
            購入
          </button>
        </div>
      </div>
      <ResultPopup result={state.commitResult} onClose={() => { store.closePopup(); showInfo(null); }} />
    </div>
  );
}
