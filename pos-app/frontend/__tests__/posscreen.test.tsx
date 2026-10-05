// 単体テスト UT-F-25, 26, 28, 30, 31（テスト仕様書 v2 の 4.2）: POS 画面とログイン画面の動き
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LoginForm } from "@/components/LoginForm";
import { PosScreen } from "@/components/PosScreen";
import { api } from "@/lib/apiClient";
import { ApiError, messageFor } from "@/lib/errors";
import type { QuoteResult } from "@/lib/types";

// 実際の useRouter は毎回同じオブジェクトを返す。テストでも同じにする（毎回新しいと再描画が止まらない）
const mockReplace = jest.fn();
const mockRouter = { replace: mockReplace, push: jest.fn() };
jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));
jest.mock("@/lib/apiClient", () => ({
  api: { login: jest.fn(), me: jest.fn(), getProduct: jest.fn(), getMember: jest.fn(), quote: jest.fn(), commit: jest.fn() },
}));
// カメラは使えないので、検出と失敗を起こすボタンに置き換える
jest.mock("@/features/scanner/CameraPreview", () => ({
  CameraPreview: (props: { onDetected: (code: string) => void; onUnavailable: () => void }) => (
    <div>
      <button onClick={() => props.onDetected("4901234567894")}>テスト用: スキャン</button>
      <button onClick={() => props.onUnavailable()}>テスト用: カメラ失敗</button>
    </div>
  ),
}));

const mocked = api as jest.Mocked<typeof api>;
const tea = { id: 1, product_code: "4901234567894", name: "緑茶 500ml", unit_price: 150 };
const quote1: QuoteResult = {
  tax_rate: 10,
  lines: [{ product_code: tea.product_code, product_name: tea.name, unit_price: 150, quantity: 1, discount: null, line_total: 150 }],
  subtotal_excl_tax: 150, tax_amount: 15, total_incl_tax: 165,
};
const serverQuote: QuoteResult = {
  tax_rate: 10,
  lines: [{ product_code: tea.product_code, product_name: tea.name, unit_price: 160, quantity: 1, discount: null, line_total: 160 }],
  subtotal_excl_tax: 160, tax_amount: 16, total_incl_tax: 176,
};

beforeEach(() => {
  jest.clearAllMocks();
  mocked.me.mockResolvedValue({ id: 1, login_id: "staff01" });
  mocked.getProduct.mockResolvedValue(tea);
  mocked.quote.mockResolvedValue(quote1);
});

async function scanOne() {
  fireEvent.click(screen.getByText("テスト用: スキャン"));
  await waitFor(() => expect(screen.getByTestId("total")).toHaveTextContent("165円"));
}

describe("POS 画面", () => {
  it("UT-F-25 ★ スキャンで追加 → 「1 件追加しました」が出る (FR-03-6, K-27, K-36)", async () => {
    render(<PosScreen />);
    await scanOne();
    expect(screen.getByTestId("message-bar")).toHaveTextContent("1 件追加しました");
    expect(screen.getByTestId("cart-row-1")).toHaveTextContent("緑茶 500ml");
    expect(mocked.quote).toHaveBeenCalledWith({ member_code: null, items: [{ product_code: tea.product_code, quantity: 1 }] });
    await waitFor(() => expect(screen.getByTestId("staff-info")).toHaveTextContent("staff01"));
  });

  it("UT-F-28 ★ 購入ボタン: リストが空のときは押せない。1 行あれば押せる (FR-08-1, K-9)", async () => {
    render(<PosScreen />);
    expect(screen.getByTestId("purchase-button")).toBeDisabled();
    await scanOne();
    expect(screen.getByTestId("purchase-button")).toBeEnabled();
  });

  it("UT-F-30 ★ 照合で不一致（409）→ 表示がサーバの金額に変わり、文言が出る。購入リストは消えない (D-008, K-37, K-36)", async () => {
    mocked.commit.mockRejectedValue(new ApiError(409, "PRICE_MISMATCH", messageFor("PRICE_MISMATCH"), { server: serverQuote }));
    render(<PosScreen />);
    await scanOne();
    fireEvent.click(screen.getByTestId("purchase-button"));
    await waitFor(() => expect(screen.getByTestId("total")).toHaveTextContent("176円"));
    expect(screen.getByTestId("message-bar")).toHaveTextContent("金額が更新されました");
    expect(screen.getByTestId("cart-row-1")).toBeInTheDocument();
    expect(screen.queryByTestId("result-popup")).toBeNull();
  });

  it("UT-F-31 ★ カメラが使えない → 「商品コードを手入力してください」が出る。手入力は使える (FR-03-3, K-37, K-36)", async () => {
    render(<PosScreen />);
    fireEvent.click(screen.getByText("テスト用: カメラ失敗"));
    await waitFor(() => expect(screen.getByTestId("message-bar")).toHaveTextContent("商品コードを手入力してください"));
    fireEvent.change(screen.getByLabelText("商品コード"), { target: { value: tea.product_code } });
    fireEvent.click(screen.getByText("商品コード読み込み"));
    await waitFor(() => expect(screen.getByTestId("pending-name")).toHaveTextContent("緑茶 500ml"));
    fireEvent.click(screen.getByText("追加"));
    await waitFor(() => expect(screen.getByTestId("cart-row-1")).toBeInTheDocument());
  });

  it("補助: 金額の計算し直しが届くまでは購入できない（古い金額で確定しない。D-008）", async () => {
    render(<PosScreen />);
    await scanOne();
    expect(screen.getByTestId("purchase-button")).toBeEnabled();
    let resolveQuote: (q: QuoteResult) => void = () => {};
    mocked.quote.mockReturnValueOnce(new Promise<QuoteResult>((r) => { resolveQuote = r; }));
    fireEvent.click(screen.getByTestId("cart-row-1"));
    fireEvent.click(screen.getByLabelText("数量を増やす")); // 数量 2 に変更 → 計算し直しを待つ
    await waitFor(() => expect(screen.getByTestId("purchase-button")).toBeDisabled());
    fireEvent.click(screen.getByTestId("purchase-button"));
    expect(mocked.commit).not.toHaveBeenCalled();
    resolveQuote({ ...quote1, lines: [{ ...quote1.lines[0], quantity: 2, line_total: 300 }], subtotal_excl_tax: 300, tax_amount: 30, total_incl_tax: 330 });
    await waitFor(() => expect(screen.getByTestId("total")).toHaveTextContent("330円"));
    expect(screen.getByTestId("purchase-button")).toBeEnabled();
  });

  it("補助: 購入が成功 → ポップアップに税込・税抜 → 閉じると空に戻る (FR-08-3, FR-08-4)", async () => {
    mocked.commit.mockResolvedValue({ transaction_id: 1, transacted_at: "2026-09-15T03:00:00Z", subtotal_excl_tax: 150, tax_amount: 15, total_incl_tax: 165 });
    render(<PosScreen />);
    await scanOne();
    fireEvent.click(screen.getByTestId("purchase-button"));
    await waitFor(() => expect(screen.getByTestId("popup-total")).toHaveTextContent("165円"));
    expect(screen.getByTestId("popup-subtotal")).toHaveTextContent("150円");
    fireEvent.click(screen.getByText("閉じる"));
    await waitFor(() => expect(screen.queryByTestId("result-popup")).toBeNull());
    expect(screen.queryByTestId("cart-row-1")).toBeNull();
    expect(screen.getByTestId("purchase-button")).toBeDisabled();
  });

  it("補助: 会員ID を読み込むと会員ID が出る。見つからなければ文言が出て会員なしのまま ★ (FR-02-6, K-6)", async () => {
    mocked.getMember.mockResolvedValueOnce({ id: 1, member_code: "M0001" });
    render(<PosScreen />);
    fireEvent.change(screen.getByLabelText("お客様ID"), { target: { value: "M0001" } });
    fireEvent.click(screen.getByText("お客様ID読み込み"));
    await waitFor(() => expect(screen.getByTestId("member-id")).toHaveTextContent("M0001"));

    mocked.getMember.mockRejectedValueOnce(new ApiError(404, "MEMBER_NOT_FOUND", messageFor("MEMBER_NOT_FOUND")));
    fireEvent.change(screen.getByLabelText("お客様ID"), { target: { value: "M9999" } });
    fireEvent.click(screen.getByText("お客様ID読み込み"));
    await waitFor(() => expect(screen.getByTestId("message-bar")).toHaveTextContent("会員が見つかりません"));
  });
});

describe("ログイン画面", () => {
  it("UT-F-26 API が 401 → 文言が出て、ログイン画面に留まる (FR-01-4)", async () => {
    mocked.login.mockRejectedValue(new ApiError(401, "AUTH_INVALID_CREDENTIALS", messageFor("AUTH_INVALID_CREDENTIALS")));
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText("担当者ID"), { target: { value: "staff01" } });
    fireEvent.change(screen.getByLabelText("パスワード"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "ログイン" }));
    await waitFor(() => expect(screen.getByTestId("login-error")).toHaveTextContent("担当者IDまたはパスワードが違います"));
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("補助: 成功したら POS 画面へ移る (FR-01-2)", async () => {
    mocked.login.mockResolvedValue({ staff: { id: 1, login_id: "staff01" } });
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText("担当者ID"), { target: { value: "staff01" } });
    fireEvent.change(screen.getByLabelText("パスワード"), { target: { value: "pos-staff-01" } });
    fireEvent.click(screen.getByRole("button", { name: "ログイン" }));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/pos"));
  });
});
