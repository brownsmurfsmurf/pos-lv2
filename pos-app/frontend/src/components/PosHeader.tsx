// レジ担当者の情報（FR-01-6）。★ 表示する内容は担当者ID（K-4）
import type { StaffInfo } from "@/lib/types";

export function PosHeader({ staff }: { staff: StaffInfo | null }) {
  return (
    <header className="pos-header">
      <h1 className="pos-header__title">簡易POS</h1>
      <div className="pos-header__staff" data-testid="staff-info">
        レジ担当者: {staff ? staff.login_id : "—"}
      </div>
    </header>
  );
}
