"use client";
// SC-01 ログイン画面（FR-01-1〜4）。失敗時は文言を出して画面に留まる
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/apiClient";
import { ApiError, messageFor } from "@/lib/errors";
import { LIMITS } from "@/lib/limits";

export function LoginForm({ onSuccess }: { onSuccess?: () => void } = {}) {
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.login({ login_id: loginId, password });
      if (onSuccess) onSuccess();
      else router.replace("/pos");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : messageFor("INTERNAL_ERROR"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="login" onSubmit={submit} aria-labelledby="login-title">
      <h1 id="login-title">簡易POS ログイン</h1>
      <label className="login__field">
        担当者ID
        <input
          className="input"
          value={loginId}
          maxLength={LIMITS.LOGIN_ID_MAX}
          autoComplete="username"
          onChange={(e) => setLoginId(e.target.value)}
          required
        />
      </label>
      <label className="login__field">
        パスワード
        <input
          className="input"
          type="password"
          value={password}
          maxLength={LIMITS.PASSWORD_MAX}
          autoComplete="current-password"
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error && (
        <div className="message message--error" role="alert" data-testid="login-error">
          {error}
        </div>
      )}
      <button type="submit" className="btn btn--primary" disabled={busy}>
        ログイン
      </button>
    </form>
  );
}
