// API-05 の BFF
import { type NextRequest } from "next/server";
import { forward, parseBody } from "@/lib/bff";
import { quoteRequestSchema } from "@/lib/schemas";

export async function POST(req: NextRequest) {
  const parsed = await parseBody(req, quoteRequestSchema);
  if (!parsed.ok) return parsed.res;
  return forward("/pricing/quote", { method: "POST", body: parsed.data });
}
