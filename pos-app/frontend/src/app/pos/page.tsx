// SC-02 POS メイン画面。Cookie がなければ /login へ（画面遷移のガード。JWT の検証は Backend）
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { PosScreen } from "@/components/PosScreen";
import { COOKIE_NAME } from "@/lib/bff";

export default async function PosPage() {
  if (!(await cookies()).get(COOKIE_NAME)) redirect("/login");
  return (
    <main className="page">
      <PosScreen />
    </main>
  );
}
