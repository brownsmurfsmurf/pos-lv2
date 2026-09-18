// SC-02-02 メッセージ表示（未登録・不存在などを伝える場所）
export function MessageBar({ message, tone = "info" }: { message: string | null; tone?: "info" | "error" }) {
  if (!message) return <div className="message message--empty" role="status" />;
  return (
    <div className={`message message--${tone}`} role="status" data-testid="message-bar">
      {message}
    </div>
  );
}
