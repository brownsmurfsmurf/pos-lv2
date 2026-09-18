// API-02 の BFF
import { forward } from "@/lib/bff";

export async function GET() {
  return forward("/auth/me");
}
