// Zod スキーマ（設計仕様書 SEC-07: 型・文字種・長さを BFF で検証し、不正なら 400 で FastAPI へ送らない）
import { z } from "zod";
import { LIMITS } from "./limits";

export const productCodeSchema = z
  .string()
  .regex(new RegExp(`^[0-9]{1,${LIMITS.PRODUCT_CODE_MAX}}$`), "商品コードは数字のみです");

export const memberCodeSchema = z
  .string()
  .regex(new RegExp(`^[A-Za-z0-9]{1,${LIMITS.MEMBER_CODE_MAX}}$`), "会員IDは半角英数字のみです");

// 型のみ検証（"2"・1.5・true は不正）。業務範囲 1〜99 は Backend のサービス層が 422 で判定する
export const quantitySchema = z.number().int();
export const moneySchema = z.number().int().min(0).max(Number.MAX_SAFE_INTEGER);

export const loginRequestSchema = z.strictObject({
  login_id: z.string().min(1).max(LIMITS.LOGIN_ID_MAX),
  password: z.string().min(1).max(LIMITS.PASSWORD_MAX),
});

export const quoteRequestSchema = z.strictObject({
  member_code: memberCodeSchema.nullable(),
  items: z
    .array(z.strictObject({ product_code: productCodeSchema, quantity: quantitySchema }))
    .max(LIMITS.CART_MAX_LINES),
});

export const commitRequestSchema = z.strictObject({
  member_code: memberCodeSchema.nullable(),
  items: z
    .array(
      z.strictObject({
        product_code: productCodeSchema,
        quantity: quantitySchema,
        unit_price: moneySchema,
        discount_amount: moneySchema,
        line_total: moneySchema,
      }),
    )
    .max(LIMITS.CART_MAX_LINES),
  tax_rate: z.number().min(0).max(100),
  subtotal_excl_tax: moneySchema,
  tax_amount: moneySchema,
  total_incl_tax: moneySchema,
});

export type LoginRequestInput = z.infer<typeof loginRequestSchema>;
export type QuoteRequestInput = z.infer<typeof quoteRequestSchema>;
export type CommitRequestInput = z.infer<typeof commitRequestSchema>;
