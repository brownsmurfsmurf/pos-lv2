// API-04 の BFF。会員IDは半角英数字のみ・長さ上限を Zod で検証（SEC-07）
import { type NextRequest } from "next/server";
import { errorResponse, forward } from "@/lib/bff";
import { memberCodeSchema } from "@/lib/schemas";

export async function GET(_req: NextRequest, ctx: { params: Promise<{ code: string }> }) {
  const { code } = await ctx.params;
  const parsed = memberCodeSchema.safeParse(code);
  if (!parsed.success) return errorResponse(400, "VALIDATION_ERROR", { fields: [{ path: ["code"] }] });
  return forward(`/members/${encodeURIComponent(parsed.data)}`);
}
