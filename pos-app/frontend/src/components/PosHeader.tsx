// SC-02-01 レジ担当者名の表示（FR-01-5）
import type { StaffInfo } from "@/lib/types";

export function PosHeader({ staff }: { staff: StaffInfo | null }) {
  return (
    <header className="pos-header">
      <h1 className="pos-header__title">簡易POS</h1>
      <div className="pos-header__staff" data-testid="staff-name">
        レジ担当者: {staff ? staff.name : "—"}
      </div>
    </header>
  );
}
