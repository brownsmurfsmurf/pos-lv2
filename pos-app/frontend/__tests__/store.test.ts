// 単体テスト UT-F-01〜14（テスト仕様書 v2 の 4.2）: 購入リストの状態
import { createCartStore } from "@/features/cart/store";
import type { ProductInfo } from "@/lib/types";

const tea: ProductInfo = { id: 1, product_code: "4901234567894", name: "緑茶 500ml", unit_price: 150 };
const bread: ProductInfo = { id: 2, product_code: "4901234567900", name: "食パン 6枚切", unit_price: 188 };
const staff = { id: 1, login_id: "staff01" };

describe("購入リスト", () => {
  it("UT-F-01 空のリストに商品 A を追加 → 1 行、数量 1 (FR-04-1, FR-04-5)", () => {
    const s = createCartStore(staff);
    expect(s.addProduct(tea)).toBe(true);
    expect(s.state.lines).toEqual([{ product_code: tea.product_code, quantity: 1 }]);
    expect(s.state.status).toBe("editing");
  });

  it("UT-F-02 同じ商品をもう一度追加 → 行は増えず、数量 2 (FR-04-4, D-003)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(tea);
    expect(s.state.lines).toHaveLength(1);
    expect(s.state.lines[0].quantity).toBe(2);
  });

  it("UT-F-03 別の商品を追加 → 2 行 (FR-04-5)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(bread);
    expect(s.state.lines.map((l) => l.product_code)).toEqual([tea.product_code, bread.product_code]);
  });

  it("UT-F-04 ★ 数量 99 の商品をさらに追加 → 99 のまま。追加できなかったと分かる (FR-05-7, K-8)", () => {
    const s = createCartStore();
    for (let i = 0; i < 99; i++) expect(s.addProduct(tea)).toBe(true);
    expect(s.addProduct(tea)).toBe(false);
    expect(s.state.lines[0].quantity).toBe(99);
  });

  it("UT-F-05 ★ 数量 1 を 0 に変更 → 変わらない (FR-05-6, K-8)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    expect(s.setQuantity(1, 0)).toBe(false);
    expect(s.state.lines[0].quantity).toBe(1);
  });

  it("UT-F-06 数量 2 を 1 に変更 → 1 になる (FR-05-5, FR-05-6)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(tea);
    expect(s.setQuantity(1, 1)).toBe(true);
    expect(s.state.lines[0].quantity).toBe(1);
  });

  it("UT-F-07 数量を 99 に変更 → 99 になる (FR-05-5, FR-05-7)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    expect(s.setQuantity(1, 99)).toBe(true);
    expect(s.state.lines[0].quantity).toBe(99);
  });

  it("UT-F-08 ★ 数量を 100 に変更 → 変わらない (FR-05-7, K-8)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.setQuantity(1, 99);
    expect(s.setQuantity(1, 100)).toBe(false);
    expect(s.state.lines[0].quantity).toBe(99);
  });

  it("UT-F-09 1 行目を選ぶ → 選択中になる (FR-05-1)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.selectLine(1);
    expect(s.state.selectedLineNo).toBe(1);
    s.selectLine(5); // 範囲外は無視
    expect(s.state.selectedLineNo).toBe(1);
  });

  it("UT-F-10 選んだ行を削除 → 行が消え、選択が外れる (FR-05-4)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(bread);
    s.selectLine(1);
    s.removeLine(1);
    expect(s.state.lines).toEqual([{ product_code: bread.product_code, quantity: 1 }]);
    expect(s.state.selectedLineNo).toBeNull();
  });

  it("UT-F-11 残り 1 行を削除 → リストが空の状態に戻る (FR-05-4)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.removeLine(1);
    expect(s.state.lines).toHaveLength(0);
    expect(s.state.status).toBe("idle");
    expect(s.state.quote).toBeNull();
  });

  it("UT-F-12 商品がある状態で会員を設定 → 会員が入り、金額の計算し直しが要求される (FR-02-3, FR-06-7, D-002)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    const before = s.state.quoteRevision;
    s.setMember({ id: 1, member_code: "M0001" });
    expect(s.state.member?.member_code).toBe("M0001");
    expect(s.state.quoteRevision).toBe(before + 1);
  });

  it("UT-F-13 手入力の 2 操作: 読み込み → 追加 (FR-03-7, FR-03-4, FR-04-1, FR-04-2, FR-04-6, D-006)", () => {
    const s = createCartStore();
    s.setPendingProduct(tea); // 読み込み: 名称・単価が入る
    expect(s.state.pendingProduct).toEqual(tea);
    expect(s.state.lines).toHaveLength(0); // まだリストには入らない
    s.addProduct(s.state.pendingProduct!); // 追加
    expect(s.state.lines).toEqual([{ product_code: tea.product_code, quantity: 1 }]);
    expect(s.state.pendingProduct).toBeNull(); // 名称・単価がクリアされる
    s.setPendingProduct(tea); // 同じ商品をもう一度 → スキャンと同じく数量が増える
    s.addProduct(s.state.pendingProduct!);
    expect(s.state.lines).toEqual([{ product_code: tea.product_code, quantity: 2 }]);
  });

  it("UT-F-14 ★ 確定成功 → ポップアップを閉じる → リスト・入力中の商品・会員ID が空。担当者は残る (FR-08-4, K-26)", () => {
    const s = createCartStore(staff);
    s.addProduct(tea);
    s.setMember({ id: 1, member_code: "M0001" });
    s.setPendingProduct(bread);
    s.commitSucceeded({ transaction_id: 1, transacted_at: "2026-09-15T03:00:00Z", subtotal_excl_tax: 240, tax_amount: 24, total_incl_tax: 264 });
    expect(s.state.status).toBe("committed");
    expect(s.addProduct(tea)).toBe(false); // 確定後は追加できない
    s.closePopup();
    expect(s.state.status).toBe("idle");
    expect(s.state.lines).toHaveLength(0);
    expect(s.state.member).toBeNull();
    expect(s.state.pendingProduct).toBeNull();
    expect(s.state.commitResult).toBeNull();
    expect(s.state.staff).toEqual(staff);
  });

  it("補助: 表示だけの変更では計算し直しを要求しない。範囲外の行番号は無視する", () => {
    const s = createCartStore();
    const listener = jest.fn();
    const unsubscribe = s.subscribe(listener);
    s.setStaff(staff);
    s.setMessage("hello");
    s.setScanMode("member");
    expect(s.state.quoteRevision).toBe(0);
    expect(listener).toHaveBeenCalledTimes(3);
    unsubscribe();
    s.setMessage(null);
    expect(listener).toHaveBeenCalledTimes(3);
    expect(s.setQuantity(1, 2)).toBe(false);
    s.removeLine(1);
    expect(s.state.lines).toHaveLength(0);
  });
});
