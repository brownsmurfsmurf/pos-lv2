// API-03 の BFF。商品コードは数字のみ・桁数上限を Zod で検証（SEC-07）
import { type NextRequest } from "next/server";
import { errorResponse, forward } from "@/lib/bff";
import { productCodeSchema } from "@/lib/schemas";

export async function GET(_req: NextRequest, ctx: { params: Promise<{ code: string }> }) {
  const { code } = await ctx.params;
  const parsed = productCodeSchema.safeParse(code);
  if (!parsed.success) return errorResponse(400, "VALIDATION_ERROR", { fields: [{ path: ["code"] }] });
  return forward(`/products/${encodeURIComponent(parsed.data)}`);
}
