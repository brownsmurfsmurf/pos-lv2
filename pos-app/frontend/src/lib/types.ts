// 共通型定義（設計仕様書 7.3 と 1 対 1）
export type Money = number; // 円の整数
export type Rate = number; // 百分率
export type DateTimeUTC = string; // ISO 8601
export type DiscountType = "percent" | "amount";

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown> };
}

export interface StaffInfo { id: number; login_id: string; name: string }
export interface ProductInfo { id: number; product_code: string; name: string; unit_price: Money }
export interface MemberInfo { id: number; member_code: string; name: string }

export interface LoginRequest { login_id: string; password: string }
export interface LoginResponse { staff: StaffInfo } // BFF はトークンを Cookie に入れ staff のみ返す

export interface QuoteItemRequest { product_code: string; quantity: number }
export interface QuoteRequest { member_code: string | null; items: QuoteItemRequest[] }
export interface AppliedDiscount { discount_id: number; type: DiscountType; value: number; amount: Money }
export interface QuoteLine {
  product_code: string;
  product_name: string;
  unit_price: Money;
  quantity: number;
  discount: AppliedDiscount | null;
  line_total: Money;
}
export interface QuoteResult {
  tax_rate: Rate;
  lines: QuoteLine[];
  subtotal_excl_tax: Money;
  tax_amount: Money;
  total_incl_tax: Money;
}

export interface CommitItem {
  product_code: string;
  quantity: number;
  unit_price: Money;
  discount_amount: Money;
  line_total: Money;
}
export interface CommitRequest {
  member_code: string | null;
  items: CommitItem[];
  tax_rate: Rate;
  subtotal_excl_tax: Money;
  tax_amount: Money;
  total_incl_tax: Money;
}
export interface CommitResponse {
  transaction_id: number;
  transacted_at: DateTimeUTC;
  subtotal_excl_tax: Money;
  tax_amount: Money;
  total_incl_tax: Money;
}
