import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "簡易POS",
  description: "Lv2 簡易POSアプリ（要求忠実版）",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
