// バーコード復号（@zxing/library のコア API）。映像フレームをグレースケールにして復号する。
import {
  BarcodeFormat, BinaryBitmap, DecodeHintType, HybridBinarizer, MultiFormatReader, NotFoundException,
  RGBLuminanceSource,
} from "@zxing/library";

const FORMATS = [
  BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.UPC_A, BarcodeFormat.UPC_E,
  BarcodeFormat.CODE_128, BarcodeFormat.CODE_39, BarcodeFormat.ITF, BarcodeFormat.QR_CODE,
];

export function createReader(): MultiFormatReader {
  const hints = new Map();
  hints.set(DecodeHintType.POSSIBLE_FORMATS, FORMATS);
  hints.set(DecodeHintType.TRY_HARDER, true);
  const reader = new MultiFormatReader();
  reader.setHints(hints);
  return reader;
}

/** ImageData → 復号した文字列。見つからなければ null。 */
export function decodeImageData(reader: MultiFormatReader, img: ImageData): string | null {
  const { width, height, data } = img;
  const gray = new Uint8ClampedArray(width * height);
  for (let i = 0, j = 0; i < data.length; i += 4, j++) {
    // 輝度（ITU-R BT.601）
    gray[j] = (data[i] * 299 + data[i + 1] * 587 + data[i + 2] * 114) / 1000;
  }
  const source = new RGBLuminanceSource(gray, width, height);
  const bitmap = new BinaryBitmap(new HybridBinarizer(source));
  try {
    return reader.decode(bitmap).getText();
  } catch (e) {
    if (e instanceof NotFoundException) return null;
    return null;
  } finally {
    reader.reset();
  }
}
