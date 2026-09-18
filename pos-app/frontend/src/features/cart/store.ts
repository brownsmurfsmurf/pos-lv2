// 購入リストの状態管理（設計仕様書 5.2）。金額の正本は Backend（quote）。ここでは行と選択と状態遷移だけを扱う。
import { LIMITS } from "@/lib/limits";
import type { CommitResponse, MemberInfo, ProductInfo, QuoteResult, StaffInfo } from "@/lib/types";

export type CartStatus = "idle" | "editing" | "committed";
export type ScanMode = "product" | "member";

export interface CartLine { product_code: string; quantity: number }

export interface CartState {
  status: CartStatus;
  staff: StaffInfo | null;
  member: MemberInfo | null;
  scanMode: ScanMode;
  pendingProduct: ProductInfo | null; // 手入力で読み込んだ、追加前の商品
  lines: CartLine[]; // 入力（金額の正本は Backend）
  catalog: Record<string, ProductInfo>; // 表示用に読み込んだ商品情報
  quote: QuoteResult | null; // API-05 の最新結果（表示用）
  selectedLineNo: number | null; // 1 始まり（transaction_items.line_no と同じ採番）
  commitResult: CommitResponse | null;
  message: string | null;
  quoteRevision: number; // 行・会員が変わるたびに増える。PosScreen が API-05 を呼ぶ契機
}

export function initialState(staff: StaffInfo | null = null): CartState {
  return {
    status: "idle",
    staff,
    member: null,
    scanMode: "product",
    pendingProduct: null,
    lines: [],
    catalog: {},
    quote: null,
    selectedLineNo: null,
    commitResult: null,
    message: null,
    quoteRevision: 0,
  };
}

type Listener = () => void;

export function createCartStore(staff: StaffInfo | null = null) {
  let state = initialState(staff);
  const listeners = new Set<Listener>();

  function set(patch: Partial<CartState>, bumpQuote = false) {
    state = { ...state, ...patch, quoteRevision: bumpQuote ? state.quoteRevision + 1 : state.quoteRevision };
    listeners.forEach((l) => l());
  }

  return {
    get state() {
      return state;
    },
    subscribe(l: Listener) {
      listeners.add(l);
      return () => listeners.delete(l);
    },

    setStaff(s: StaffInfo | null) {
      set({ staff: s });
    },
    setMessage(message: string | null) {
      set({ message });
    },
    setScanMode(scanMode: ScanMode) {
      set({ scanMode });
    },
    setPendingProduct(p: ProductInfo | null) {
      set({ pendingProduct: p });
    },

    /** FR-04-1/4/5: 同一商品は数量加算、なければ新規行。上限 99 なら加算しない（★ Q-2）。戻り値は追加できたか。 */
    addProduct(p: ProductInfo): boolean {
      if (state.status === "committed") return false;
      const idx = state.lines.findIndex((l) => l.product_code === p.product_code);
      let lines: CartLine[];
      if (idx >= 0) {
        if (state.lines[idx].quantity >= LIMITS.QTY_MAX) return false;
        lines = state.lines.map((l, i) => (i === idx ? { ...l, quantity: l.quantity + 1 } : l));
      } else {
        if (state.lines.length >= LIMITS.CART_MAX_LINES) return false;
        lines = [...state.lines, { product_code: p.product_code, quantity: 1 }];
      }
      set(
        {
          lines,
          catalog: { ...state.catalog, [p.product_code]: p },
          pendingProduct: null, // FR-04-2: 追加後に入力表示を空に戻す
          status: "editing",
        },
        true,
      );
      return true;
    },

    /** FR-05-1: 行の選択（null で解除） */
    selectLine(lineNo: number | null) {
      if (lineNo !== null && (lineNo < 1 || lineNo > state.lines.length)) return;
      set({ selectedLineNo: lineNo });
    },

    /** FR-05-5〜7: 数量変更。1〜99 の外なら変更せず false を返す（0 にしたいときは削除する） */
    setQuantity(lineNo: number, quantity: number): boolean {
      if (!Number.isInteger(quantity) || quantity < LIMITS.QTY_MIN || quantity > LIMITS.QTY_MAX) return false;
      if (lineNo < 1 || lineNo > state.lines.length) return false;
      const lines = state.lines.map((l, i) => (i === lineNo - 1 ? { ...l, quantity } : l));
      set({ lines }, true);
      return true;
    },

    /** FR-05-4: 行の削除。選択は解除。全行なくなれば idle に戻る */
    removeLine(lineNo: number) {
      if (lineNo < 1 || lineNo > state.lines.length) return;
      const lines = state.lines.filter((_, i) => i !== lineNo - 1);
      set(
        {
          lines,
          selectedLineNo: null,
          status: lines.length === 0 ? "idle" : "editing",
          quote: lines.length === 0 ? null : state.quote,
        },
        true,
      );
    },

    /** FR-02-3/FR-06-7: 会員はいつでも設定できる。登録済みの行にも値引きを付け直すため再見積を要求する */
    setMember(m: MemberInfo | null) {
      set({ member: m }, true);
    },

    setQuote(q: QuoteResult | null) {
      set({ quote: q });
    },

    /** FR-08-1〜3: 確定成功。ポップアップ表示状態へ */
    commitSucceeded(result: CommitResponse) {
      set({ status: "committed", commitResult: result, message: null });
    },

    /** FR-08-4: ポップアップを閉じたら入力欄・購入リスト・会員を空にして最初に戻る（担当者は保持） */
    closePopup() {
      set(initialState(state.staff));
    },
  };
}

export type CartStore = ReturnType<typeof createCartStore>;
