// UT-F-06〜18（テスト仕様書 5.2）: features/cart/store.ts の状態遷移
import { createCartStore } from "@/features/cart/store";
import type { ProductInfo } from "@/lib/types";

const tea: ProductInfo = { id: 1, product_code: "4901234567894", name: "緑茶 500ml", unit_price: 150 };
const bread: ProductInfo = { id: 2, product_code: "4901234567900", name: "食パン 6枚切", unit_price: 188 };
const staff = { id: 1, login_id: "staff01", name: "佐藤 花子" };

describe("cart store", () => {
  it("UT-F-06 空に A を追加 → 1 行 数量 1、状態 editing (FR-04-1)", () => {
    const s = createCartStore(staff);
    expect(s.addProduct(tea)).toBe(true);
    expect(s.state.lines).toEqual([{ product_code: tea.product_code, quantity: 1 }]);
    expect(s.state.status).toBe("editing");
    expect(s.state.quoteRevision).toBe(1);
  });

  it("UT-F-07 同じ商品を続けて追加すると数量を加算する (FR-04-4)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(tea);
    expect(s.state.lines).toHaveLength(1);
    expect(s.state.lines[0].quantity).toBe(2);
  });

  it("UT-F-08 別商品は新しい行 (FR-04-5)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(bread);
    expect(s.state.lines.map((l) => l.product_code)).toEqual([tea.product_code, bread.product_code]);
  });

  it("UT-F-09/10 A を 99 回 → 99、100 回目は増えない ★ (FR-05-7, Q-2)", () => {
    const s = createCartStore();
    for (let i = 0; i < 99; i++) expect(s.addProduct(tea)).toBe(true);
    expect(s.state.lines[0].quantity).toBe(99);
    expect(s.addProduct(tea)).toBe(false);
    expect(s.state.lines[0].quantity).toBe(99);
  });

  it("UT-F-11〜13 数量 99 は反映、0 と 100 は変わらない (FR-05-5〜7)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    expect(s.setQuantity(1, 99)).toBe(true);
    expect(s.state.lines[0].quantity).toBe(99);
    expect(s.setQuantity(1, 0)).toBe(false);
    expect(s.state.lines[0].quantity).toBe(99);
    expect(s.setQuantity(1, 100)).toBe(false);
    expect(s.state.lines[0].quantity).toBe(99);
    expect(s.setQuantity(1, 1.5)).toBe(false);
  });

  it("UT-F-14 行を選んで削除 → 行が消え選択解除 (FR-05-1, FR-05-4)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.addProduct(bread);
    s.selectLine(1);
    expect(s.state.selectedLineNo).toBe(1);
    s.removeLine(1);
    expect(s.state.lines).toEqual([{ product_code: bread.product_code, quantity: 1 }]);
    expect(s.state.selectedLineNo).toBeNull();
    expect(s.state.status).toBe("editing");
  });

  it("UT-F-15 全行削除 → 状態 idle", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.removeLine(1);
    expect(s.state.lines).toHaveLength(0);
    expect(s.state.status).toBe("idle");
    expect(s.state.quote).toBeNull();
  });

  it("UT-F-16 会員を設定 → member が入り再計算が要求される (FR-02-3, FR-06-7)", () => {
    const s = createCartStore();
    s.addProduct(tea);
    const before = s.state.quoteRevision;
    s.setMember({ id: 1, member_code: "M0001", name: "山田 太郎" });
    expect(s.state.member?.name).toBe("山田 太郎");
    expect(s.state.quoteRevision).toBe(before + 1);
  });

  it("UT-F-17 確定成功 → 閉じる → idle、行・会員・入力中の商品が空。担当者は保持 (FR-08-4)", () => {
    const s = createCartStore(staff);
    s.addProduct(tea);
    s.setMember({ id: 1, member_code: "M0001", name: "山田 太郎" });
    s.setPendingProduct(bread);
    s.commitSucceeded({ transaction_id: 1, transacted_at: "2026-09-15T03:00:00Z", subtotal_excl_tax: 150, tax_amount: 15, total_incl_tax: 165 });
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

  it("UT-F-18 手入力で読み込み → 追加 → 入力中の商品が空に戻る (FR-04-2)", () => {
    const s = createCartStore();
    s.setPendingProduct(tea);
    expect(s.state.pendingProduct).toEqual(tea);
    s.addProduct(s.state.pendingProduct!);
    expect(s.state.pendingProduct).toBeNull();
    expect(s.state.catalog[tea.product_code]).toEqual(tea);
  });

  it("selectLine は範囲外を無視する", () => {
    const s = createCartStore();
    s.addProduct(tea);
    s.selectLine(5);
    expect(s.state.selectedLineNo).toBeNull();
    s.selectLine(1);
    s.selectLine(null);
    expect(s.state.selectedLineNo).toBeNull();
  });
});
