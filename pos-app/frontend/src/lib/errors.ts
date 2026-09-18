// エラーコードと画面の文言（設計仕様書 11.2）。Frontend は code で動作を決め、文言はここから引く（ERR-3）
export const ERROR_MESSAGES: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: "担当者IDまたはパスワードが違います",
  AUTH_REQUIRED: "再度ログインしてください",
  VALIDATION_ERROR: "入力内容に誤りがあります",
  PRODUCT_NOT_FOUND: "商品がマスタ未登録です", // 要求一覧の文言そのまま（FR-03-5）
  MEMBER_NOT_FOUND: "該当する会員が見つかりません",
  QUANTITY_OUT_OF_RANGE: "数量は 1〜99 で指定してください",
  CART_EMPTY: "商品が登録されていません",
  TAX_RATE_NOT_CONFIGURED: "消費税率が設定されていません",
  PRICE_MISMATCH: "金額が更新されました。内容を確認して再度購入してください",
  INTERNAL_ERROR: "処理に失敗しました。もう一度お試しください",
  SERVICE_UNAVAILABLE: "サービスに接続できません",
  // Frontend のみ
  CAMERA_UNAVAILABLE: "カメラを使用できません。商品コードを手入力してください",
};

export const ADDED_MESSAGE = "1 件追加しました"; // SC-02-13（FR-03-6）

export function messageFor(code: string, fallback?: string): string {
  return ERROR_MESSAGES[code] ?? fallback ?? ERROR_MESSAGES.INTERNAL_ERROR;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}
