// 制約値（設計仕様書 10 章）。正本は pos-app/shared/limits.json。limits.json は sync-limits で写される。
import data from "./limits.json";

export interface Limits {
  QTY_MIN: number;
  QTY_MAX: number;
  CART_MAX_LINES: number;
  PRODUCT_CODE_MAX: number;
  MEMBER_CODE_MAX: number;
  LOGIN_ID_MAX: number;
  PASSWORD_MIN: number;
  PASSWORD_MAX: number;
  PRICE_MAX: number;
  TAX_ROUNDING: "floor";
  DISCOUNT_ROUNDING: "floor";
  DISCOUNT_SELECTION: "max_amount";
  JWT_TTL_HOURS: number;
  SCAN_DEBOUNCE_MS: number;
  BODY_MAX_BYTES: number;
  BUSINESS_TIMEZONE: string;
}

export const LIMITS: Limits = data as Limits;
