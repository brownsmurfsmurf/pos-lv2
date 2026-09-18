"use client";
// SC-02-03〜06 お客様ID入力欄／会員証スキャン／お客様ID読み込みボタン／お客様名（FR-02）
import { useState } from "react";
import { LIMITS } from "@/lib/limits";
import type { MemberInfo } from "@/lib/types";

interface Props {
  member: MemberInfo | null;
  scanMode: "product" | "member";
  onRead: (code: string) => void; // 空なら「会員なしで進む」（FR-02-7、I-5）
  onStartScan: () => void;
}

export function MemberPanel({ member, scanMode, onRead, onStartScan }: Props) {
  const [code, setCode] = useState("");
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
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onRead(code);
              setCode("");
            }
          }}
        />
        <button
          type="button"
          className="btn"
          onClick={() => {
            onRead(code);
            setCode("");
          }}
        >
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
      <div className="field" data-testid="member-name">
        お客様名: <strong>{member ? member.name : "（会員なし）"}</strong>
      </div>
    </section>
  );
}
