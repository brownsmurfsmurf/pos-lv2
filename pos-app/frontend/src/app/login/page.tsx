// SC-01 ログイン画面。Cookie があれば /pos へ（本当の検証は Backend の JWT 検証）
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LoginForm } from "@/components/LoginForm";
import { COOKIE_NAME } from "@/lib/bff";

export default async function LoginPage() {
  if ((await cookies()).get(COOKIE_NAME)) redirect("/pos");
  return (
    <main className="page page--center">
      <LoginForm />
    </main>
  );
}
