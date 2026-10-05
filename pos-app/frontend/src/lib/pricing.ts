// 金額の表示形式だけを扱う。金額の計算（値引き・税・合計）はサーバだけが行う（D-008）
import type { Money } from "./types";

export function formatYen(v: Money): string {
  return `${v.toLocaleString("ja-JP")}円`;
}
