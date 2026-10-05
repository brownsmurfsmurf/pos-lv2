// 単体テスト UT-F-17〜24, UT-F-29（テスト仕様書 v2 の 4.2）: 画面の部品の表示
import { fireEvent, render, screen } from "@testing-library/react";
import { CartTable } from "@/components/CartTable";
import { MemberPanel } from "@/components/MemberPanel";
import { MessageBar } from "@/components/MessageBar";
import { PosHeader } from "@/components/PosHeader";
import { ProductEntryPanel } from "@/components/ProductEntryPanel";
import { ResultPopup } from "@/components/ResultPopup";
import { SelectedItemPanel } from "@/components/SelectedItemPanel";
import { TotalsPanel } from "@/components/TotalsPanel";
import { ERROR_MESSAGES } from "@/lib/errors";
import type { QuoteResult } from "@/lib/types";

// E-2 の条件: 188 円 × 1（値引きなし）と 150 円 × 2（20% 引き）→ 税抜 428、税 42、税込 470
const quote: QuoteResult = {
  tax_rate: 10,
  lines: [
    { product_code: "4901234567900", product_name: "食パン 6枚切", unit_price: 188, quantity: 1, discount: null, line_total: 188 },
    { product_code: "4901234567894", product_name: "緑茶 500ml", unit_price: 150, quantity: 2,
      discount: { discount_id: 1, type: "percent", value: 20, amount: 60 }, line_total: 240 },
  ],
  subtotal_excl_tax: 428, tax_amount: 42, total_incl_tax: 470,
};
const lines = [{ product_code: "4901234567900", quantity: 1 }, { product_code: "4901234567894", quantity: 2 }];

describe("画面の部品", () => {
  it("UT-F-17 商品が見つからない → 「商品がマスタ未登録です」が出る (FR-03-5)", () => {
    render(<MessageBar message={ERROR_MESSAGES.PRODUCT_NOT_FOUND} tone="error" />);
    expect(screen.getByRole("status")).toHaveTextContent("商品がマスタ未登録です");
  });

  it("UT-F-18 選んだ行だけ強調される (FR-05-2)", () => {
    const onSelect = jest.fn();
    render(<CartTable lines={lines} catalog={{}} quote={quote} selectedLineNo={1} onSelect={onSelect} />);
    expect(screen.getByTestId("cart-row-1")).toHaveClass("cart__row--selected");
    expect(screen.getByTestId("cart-row-2")).not.toHaveClass("cart__row--selected");
    fireEvent.click(screen.getByTestId("cart-row-2"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("UT-F-19 選択中の商品の名称・単価・数量が出る (FR-05-3)。数量の変更と削除ができる (FR-05-4, FR-05-5)", () => {
    const onChange = jest.fn();
    const onRemove = jest.fn();
    render(<SelectedItemPanel line={lines[1]} product={null} quoteLine={quote.lines[1]} onChangeQuantity={onChange} onRemove={onRemove} />);
    const panel = screen.getByTestId("selected-panel");
    expect(panel).toHaveTextContent("緑茶 500ml");
    expect(panel).toHaveTextContent("150円");
    expect(screen.getByLabelText("数量")).toHaveValue(2);
    fireEvent.click(screen.getByLabelText("数量を増やす"));
    expect(onChange).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByLabelText("数量を減らす"));
    expect(onChange).toHaveBeenCalledWith(1);
    fireEvent.change(screen.getByLabelText("数量"), { target: { value: "5" } });
    expect(onChange).toHaveBeenCalledWith(5);
    fireEvent.click(screen.getByText("削除"));
    expect(onRemove).toHaveBeenCalled();
  });

  it("UT-F-20 購入リストに名称・数量・単価・値引き額・小計が出る (FR-04-7, FR-06-5)", () => {
    render(<CartTable lines={lines} catalog={{}} quote={quote} selectedLineNo={null} onSelect={() => {}} />);
    const row = screen.getByTestId("cart-row-2");
    expect(row).toHaveTextContent("緑茶 500ml");
    expect(row).toHaveTextContent("2");
    expect(row).toHaveTextContent("150円");
    expect(row).toHaveTextContent("−60円");
    expect(row).toHaveTextContent("240円");
    expect(screen.getByTestId("cart-row-1")).not.toHaveTextContent("−");
  });

  it("UT-F-21 ★ 合計に税抜合計と税込合計が出る (FR-05-8, FR-07-1, K-25)", () => {
    render(<TotalsPanel quote={quote} />);
    expect(screen.getByTestId("subtotal")).toHaveTextContent("428円");
    expect(screen.getByTestId("total")).toHaveTextContent("470円");
  });

  it("UT-F-22 ポップアップに税込合計と税抜合計が出る。閉じるが押せる (FR-08-3, FR-07-1)", () => {
    const onClose = jest.fn();
    render(<ResultPopup result={{ transaction_id: 7, transacted_at: "2026-09-15T03:00:00Z", subtotal_excl_tax: 428, tax_amount: 42, total_incl_tax: 470 }} onClose={onClose} />);
    expect(screen.getByTestId("popup-total")).toHaveTextContent("470円");
    expect(screen.getByTestId("popup-subtotal")).toHaveTextContent("428円");
    fireEvent.click(screen.getByText("閉じる"));
    expect(onClose).toHaveBeenCalled();
  });

  it("UT-F-23 ★ 担当者ID が出る (FR-01-6, K-4)", () => {
    render(<PosHeader staff={{ id: 1, login_id: "staff01" }} />);
    expect(screen.getByTestId("staff-info")).toHaveTextContent("staff01");
  });

  it("UT-F-24 ★ 会員ID が出る。氏名は出ない (FR-02-4, K-5)", () => {
    render(<MemberPanel member={{ id: 1, member_code: "M0001" }} scanMode="member" onRead={() => {}} onStartScan={() => {}} />);
    expect(screen.getByTestId("member-id")).toHaveTextContent("M0001");
    expect(screen.queryByText(/山田/)).toBeNull();
    expect(screen.getByText("会員証スキャン")).toHaveAttribute("aria-pressed", "true");
  });

  it("UT-F-29 お客様ID を空のまま読み込みボタン → エラーにならず、会員なしで進む (FR-02-7, D-005)", () => {
    const onRead = jest.fn();
    const onStartScan = jest.fn();
    render(<MemberPanel member={null} scanMode="product" onRead={onRead} onStartScan={onStartScan} />);
    fireEvent.click(screen.getByText("お客様ID読み込み"));
    expect(onRead).toHaveBeenCalledWith("");
    expect(screen.getByTestId("member-id")).toHaveTextContent("（会員なし）");
    // 入力して Enter でも読み込める (FR-02-2)
    const input = screen.getByLabelText("お客様ID");
    fireEvent.change(input, { target: { value: " M0001 " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRead).toHaveBeenCalledWith("M0001");
    fireEvent.click(screen.getByText("会員証スキャン"));
    expect(onStartScan).toHaveBeenCalled();
  });

  it("補助: 手入力の欄。読み込み前は追加が押せない。空では読み込まない (FR-03-7, FR-04-1)", () => {
    const onRead = jest.fn();
    const onAdd = jest.fn();
    const { rerender } = render(<ProductEntryPanel pendingProduct={null} addedFlash={false} onRead={onRead} onAdd={onAdd} />);
    expect(screen.getByText("追加")).toBeDisabled();
    const input = screen.getByLabelText("商品コード");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRead).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "4901234567894" } });
    fireEvent.click(screen.getByText("商品コード読み込み"));
    expect(onRead).toHaveBeenCalledWith("4901234567894");
    rerender(<ProductEntryPanel pendingProduct={{ id: 1, product_code: "4901234567894", name: "緑茶 500ml", unit_price: 150 }} addedFlash={false} onRead={onRead} onAdd={onAdd} />);
    expect(screen.getByTestId("pending-name")).toHaveTextContent("緑茶 500ml");
    expect(screen.getByTestId("pending-price")).toHaveTextContent("150円");
    fireEvent.click(screen.getByText("追加"));
    expect(onAdd).toHaveBeenCalled();
  });

  it("補助: 何もないときの表示", () => {
    render(<MessageBar message={null} />);
    expect(screen.queryByTestId("message-bar")).toBeNull();
    render(<ResultPopup result={null} onClose={() => {}} />);
    expect(screen.queryByTestId("result-popup")).toBeNull();
    render(<SelectedItemPanel line={null} product={null} quoteLine={null} onChangeQuantity={() => {}} onRemove={() => {}} />);
    expect(screen.getByText(/行を選ぶと/)).toBeInTheDocument();
    render(<PosHeader staff={null} />);
    render(<TotalsPanel quote={null} />);
    render(<CartTable lines={[]} catalog={{}} quote={null} selectedLineNo={null} onSelect={() => {}} />);
    expect(screen.getByText("商品が登録されていません")).toBeInTheDocument();
  });
});
