// ★ 同じバーコードの連続読み取りを無視する（設計仕様書 v2 の 3 章。K-34）。
// カメラは同じコードを毎フレーム読むので、直前と同じコードは windowMs 以内なら受け付けない。
// 「以内」なので、ちょうど windowMs 後も無視する。windowMs を 1 ミリ秒でも超えたら受け付ける。
export interface ScanGate {
  accept(code: string, nowMs: number): boolean;
}

export function createScanGate(windowMs: number): ScanGate {
  let lastCode: string | null = null;
  let lastAt = 0;
  return {
    accept(code, nowMs) {
      if (code === lastCode && nowMs - lastAt <= windowMs) return false;
      lastCode = code;
      lastAt = nowMs;
      return true;
    },
  };
}
