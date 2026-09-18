// API-06 の BFF
import { type NextRequest } from "next/server";
import { forward, parseBody } from "@/lib/bff";
import { commitRequestSchema } from "@/lib/schemas";

export async function POST(req: NextRequest) {
  const parsed = await parseBody(req, commitRequestSchema);
  if (!parsed.ok) return parsed.res;
  return forward("/transactions", { method: "POST", body: parsed.data });
}
