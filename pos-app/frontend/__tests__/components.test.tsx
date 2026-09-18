// UT-F-26〜35（テスト仕様書 5.2）: 画面部品の表示
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

const quote: QuoteResult = {
  tax_rate: 10,
  lines: [
    { product_code: "4901234567894", product_name: "緑茶 500ml", unit_price: 150, quantity: 2,
      discount: { discount_id: 1, type: "percent", value: 20, amount: 60 }, line_total: 240 },
    { product_code: "4901234567900", product_name: "食パン 6枚切", unit_price: 188, quantity: 1, discount: null, line_total: 188 },
  ],
  subtotal_excl_tax: 428, tax_amount: 42, total_incl_tax: 470,
};
const lines = [{ product_code: "4901234567894", quantity: 2 }, { product_code: "4901234567900", quantity: 1 }];

describe("表示部品", () => {
  it("UT-F-26 「商品がマスタ未登録です」の文言が出る (FR-03-5)", () => {
    render(<MessageBar message={ERROR_MESSAGES.PRODUCT_NOT_FOUND} tone="error" />);
    expect(screen.getByRole("status")).toHaveTextContent("商品がマスタ未登録です");
  });

  it("UT-F-27 会員が見つからない旨が出る (FR-02-6)", () => {
    render(<MessageBar message={ERROR_MESSAGES.MEMBER_NOT_FOUND} tone="error" />);
    expect(screen.getByTestId("message-bar")).toHaveTextContent("該当する会員が見つかりません");
  });

  it("UT-F-28 選んだ行が強調される (FR-05-2)", () => {
    const onSelect = jest.fn();
    render(<CartTable lines={lines} catalog={{}} quote={quote} selectedLineNo={1} onSelect={onSelect} />);
    expect(screen.getByTestId("cart-row-1")).toHaveClass("cart__row--selected");
    expect(screen.getByTestId("cart-row-2")).not.toHaveClass("cart__row--selected");
    fireEvent.click(screen.getByTestId("cart-row-2"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("UT-F-29 値引き額（−60円）が出る (FR-06-5)", () => {
    render(<CartTable lines={lines} catalog={{}} quote={quote} selectedLineNo={null} onSelect={() => {}} />);
    expect(screen.getByTestId("cart-row-1")).toHaveTextContent("−60円");
    expect(screen.getByTestId("cart-row-1")).toHaveTextContent("240円");
  });

  it("UT-F-30 選んだ商品の名称・単価・数量が出る (FR-05-3)", () => {
    render(<SelectedItemPanel line={lines[0]} product={null} quoteLine={quote.lines[0]} onChangeQuantity={() => {}} onRemove={() => {}} />);
    const panel = screen.getByTestId("selected-panel");
    expect(panel).toHaveTextContent("緑茶 500ml");
    expect(panel).toHaveTextContent("150円");
    expect(screen.getByLabelText("数量")).toHaveValue(2);
  });

  it("UT-F-31 ＋／−／削除が呼ばれる (FR-05-4, FR-05-5)", () => {
    const onChange = jest.fn();
    const onRemove = jest.fn();
    render(<SelectedItemPanel line={lines[0]} product={null} quoteLine={quote.lines[0]} onChangeQuantity={onChange} onRemove={onRemove} />);
    fireEvent.click(screen.getByLabelText("数量を増やす"));
    expect(onChange).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByLabelText("数量を減らす"));
    expect(onChange).toHaveBeenCalledWith(1);
    fireEvent.click(screen.getByText("削除"));
    expect(onRemove).toHaveBeenCalled();
  });

  it("UT-F-32 税抜・税込の合計が出る (FR-05-8)", () => {
    render(<TotalsPanel quote={quote} />);
    expect(screen.getByTestId("subtotal")).toHaveTextContent("428円");
    expect(screen.getByTestId("tax")).toHaveTextContent("42円");
    expect(screen.getByTestId("total")).toHaveTextContent("470円");
  });

  it("UT-F-33 ポップアップに税込・税抜の両方が出て、閉じるで onClose (FR-07-1, FR-08-3/4)", () => {
    const onClose = jest.fn();
    render(<ResultPopup result={{ transaction_id: 7, transacted_at: "2026-09-15T03:00:00Z", subtotal_excl_tax: 428, tax_amount: 42, total_incl_tax: 470 }} onClose={onClose} />);
    expect(screen.getByTestId("popup-subtotal")).toHaveTextContent("428円");
    expect(screen.getByTestId("popup-total")).toHaveTextContent("470円");
    fireEvent.click(screen.getByText("閉じる"));
    expect(onClose).toHaveBeenCalled();
  });

  it("UT-F-34 「1 件追加」が出る (FR-03-6)、追加ボタンは読み込み前は無効", () => {
    const onRead = jest.fn();
    const { rerender } = render(<ProductEntryPanel pendingProduct={null} addedFlash={false} onRead={onRead} onAdd={() => {}} />);
    expect(screen.getByText("追加")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("商品コード"), { target: { value: "4901234567894" } });
    fireEvent.click(screen.getByText("商品コード読み込み"));
    expect(onRead).toHaveBeenCalledWith("4901234567894");
    rerender(<ProductEntryPanel pendingProduct={{ id: 1, product_code: "4901234567894", name: "緑茶 500ml", unit_price: 150 }} addedFlash={true} onRead={onRead} onAdd={() => {}} />);
    expect(screen.getByTestId("pending-name")).toHaveTextContent("緑茶 500ml");
    expect(screen.getByTestId("added-indicator")).toHaveTextContent("1 件追加");
  });

  it("UT-F-35 担当者名が出る (FR-01-5)、会員なしでも読み込みボタンで進める (FR-02-7)", () => {
    render(<PosHeader staff={{ id: 1, login_id: "staff01", name: "佐藤 花子" }} />);
    expect(screen.getByTestId("staff-name")).toHaveTextContent("佐藤 花子");
    const onRead = jest.fn();
    render(<MemberPanel member={null} scanMode="product" onRead={onRead} onStartScan={() => {}} />);
    fireEvent.click(screen.getByText("お客様ID読み込み"));
    expect(onRead).toHaveBeenCalledWith("");
    expect(screen.getByTestId("member-name")).toHaveTextContent("（会員なし）");
  });

  it("MemberPanel: Enter で読み込み、会員証スキャンボタンで onStartScan (FR-02-1/2)", () => {
    const onRead = jest.fn();
    const onStartScan = jest.fn();
    render(<MemberPanel member={{ id: 1, member_code: "M0001", name: "山田 太郎" }} scanMode="member" onRead={onRead} onStartScan={onStartScan} />);
    const input = screen.getByLabelText("お客様ID");
    fireEvent.change(input, { target: { value: " M0001 " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRead).toHaveBeenCalledWith("M0001");
    expect(input).toHaveValue("");
    fireEvent.click(screen.getByText("会員証スキャン"));
    expect(onStartScan).toHaveBeenCalled();
    expect(screen.getByText("会員証スキャン")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("member-name")).toHaveTextContent("山田 太郎");
  });

  it("SelectedItemPanel: 未選択時は案内文、数量の直接入力で onChangeQuantity (Q-1 ★)", () => {
    const { rerender } = render(<SelectedItemPanel line={null} product={null} quoteLine={null} onChangeQuantity={() => {}} onRemove={() => {}} />);
    expect(screen.getByText(/行を選ぶと/)).toBeInTheDocument();
    const onChange = jest.fn();
    rerender(<SelectedItemPanel line={lines[1]} product={{ id: 2, product_code: "4901234567900", name: "食パン 6枚切", unit_price: 188 }} quoteLine={null} onChangeQuantity={onChange} onRemove={() => {}} />);
    fireEvent.change(screen.getByLabelText("数量"), { target: { value: "5" } });
    expect(onChange).toHaveBeenCalledWith(5);
    expect(screen.getByTestId("selected-panel")).toHaveTextContent("食パン 6枚切");
  });

  it("ProductEntryPanel: Enter で読み込み、空なら呼ばない。MessageBar は空なら何も出さない", () => {
    const onRead = jest.fn();
    render(<ProductEntryPanel pendingProduct={null} addedFlash={false} onRead={onRead} onAdd={() => {}} />);
    const input = screen.getByLabelText("商品コード");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRead).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "4901234567894" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRead).toHaveBeenCalledWith("4901234567894");
    render(<MessageBar message={null} />);
    expect(screen.queryByTestId("message-bar")).toBeNull();
    render(<ResultPopup result={null} onClose={() => {}} />);
    expect(screen.queryByTestId("result-popup")).toBeNull();
  });
});
