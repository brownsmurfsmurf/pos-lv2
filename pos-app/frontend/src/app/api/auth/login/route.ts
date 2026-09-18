// API-01 の BFF。ログイン成功時に access_token を Cookie に格納し、ブラウザには staff のみ返す（7.4）
import { NextResponse, type NextRequest } from "next/server";
import { forward, parseBody, setTokenCookie } from "@/lib/bff";
import { loginRequestSchema } from "@/lib/schemas";

interface UpstreamLogin {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
  staff: { id: number; login_id: string; name: string };
}

export async function POST(req: NextRequest) {
  const parsed = await parseBody(req, loginRequestSchema);
  if (!parsed.ok) return parsed.res;

  const upstream = await forward("/auth/login", { method: "POST", body: parsed.data, auth: false });
  if (upstream.status !== 200) return upstream;

  const body = (await upstream.json()) as UpstreamLogin;
  const res = NextResponse.json({ staff: body.staff });
  setTokenCookie(res, body.access_token, body.expires_in);
  return res;
}
