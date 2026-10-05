"use client";
// お客様ID 入力欄／読み込みボタン／会員ID の表示／読み取り先の切り替え（FR-02、D-005）
import { useState } from "react";
import { LIMITS } from "@/lib/limits";
import type { MemberInfo } from "@/lib/types";

interface Props {
  member: MemberInfo | null;
  scanMode: "product" | "member";
  onRead: (code: string) => void; // 空のまま押せば会員なしで進む（FR-02-7。押すのは任意。D-005）
  onStartScan: () => void; // ★ カメラの読み取り先を会員証に切り替える（K-24）
}

export function MemberPanel({ member, scanMode, onRead, onStartScan }: Props) {
  const [code, setCode] = useState("");
  const read = () => {
    onRead(code);
    setCode("");
  };
  return (
    <section className="panel" aria-labelledby="member-heading">
      <h2 id="member-heading" className="panel__title">お客様</h2>
      <div className="row">
        <input
          className="input"
          aria-label="お客様ID"
          placeholder="お客様ID（会員ID）"
          value={code}
          maxLength={LIMITS.MEMBER_CODE_MAX}
          onChange={(e) => setCode(e.target.value.trim())}
          onKeyDown={(e) => e.key === "Enter" && read()}
        />
        <button type="button" className="btn" onClick={read}>
          お客様ID読み込み
        </button>
        <button
          type="button"
          className={`btn ${scanMode === "member" ? "btn--active" : ""}`}
          onClick={onStartScan}
          aria-pressed={scanMode === "member"}
        >
          会員証スキャン
        </button>
      </div>
      {/* FR-02-4: 会員ID を表示する。氏名は表示しない（K-5） */}
      <div className="field" data-testid="member-id">
        会員ID: <strong>{member ? member.member_code : "（会員なし）"}</strong>
      </div>
    </section>
  );
}
