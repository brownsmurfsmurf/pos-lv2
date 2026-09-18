// エラーコード → 文言（設計仕様書 11.2 ERR-3）
import { ApiError, ERROR_MESSAGES, messageFor } from "@/lib/errors";
import { createCartStore } from "@/features/cart/store";

describe("messageFor", () => {
  it("要求一覧の文言をそのまま使う (FR-03-5)", () => {
    expect(messageFor("PRODUCT_NOT_FOUND")).toBe("商品がマスタ未登録です");
  });
  it("未知のコードは fallback、なければ INTERNAL_ERROR の文言", () => {
    expect(messageFor("UNKNOWN", "サーバの文言")).toBe("サーバの文言");
    expect(messageFor("UNKNOWN")).toBe(ERROR_MESSAGES.INTERNAL_ERROR);
  });
  it("ApiError は status / code / details を持つ", () => {
    const e = new ApiError(409, "PRICE_MISMATCH", messageFor("PRICE_MISMATCH"), { server: {} });
    expect(e).toBeInstanceOf(Error);
    expect(e.status).toBe(409);
    expect(e.code).toBe("PRICE_MISMATCH");
    expect(e.details).toEqual({ server: {} });
    expect(e.message).toContain("金額が更新されました");
  });
});

describe("store の補助操作", () => {
  it("setStaff / setMessage / setScanMode / subscribe", () => {
    const s = createCartStore();
    const listener = jest.fn();
    const unsubscribe = s.subscribe(listener);
    s.setStaff({ id: 1, login_id: "staff01", name: "佐藤 花子" });
    s.setMessage("hello");
    s.setScanMode("member");
    expect(s.state.staff?.name).toBe("佐藤 花子");
    expect(s.state.message).toBe("hello");
    expect(s.state.scanMode).toBe("member");
    expect(listener).toHaveBeenCalledTimes(3);
    unsubscribe();
    s.setMessage(null);
    expect(listener).toHaveBeenCalledTimes(3);
    expect(s.state.quoteRevision).toBe(0); // 表示系の変更では再見積を要求しない
  });
  it("setQuantity / removeLine は範囲外の行番号を無視する", () => {
    const s = createCartStore();
    expect(s.setQuantity(1, 2)).toBe(false);
    s.removeLine(1);
    expect(s.state.lines).toHaveLength(0);
  });
});
