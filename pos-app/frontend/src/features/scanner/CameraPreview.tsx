"use client";
// SC-02-07 カメラ映像（FR-03-1/2）。連続して読み取り、同一コードの連続検出は SCAN_DEBOUNCE_MS 無視する（★）。
import { useEffect, useRef } from "react";
import { LIMITS } from "@/lib/limits";
import { createReader, decodeImageData } from "./decoder";

interface Props {
  active: boolean;
  label: string; // 何を読み取るモードか（商品 / 会員証）
  onDetected: (code: string) => void;
  onUnavailable: () => void;
}

const FRAME_INTERVAL_MS = 150;

export function CameraPreview({ active, label, onDetected, onUnavailable }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const onDetectedRef = useRef(onDetected);
  const onUnavailableRef = useRef(onUnavailable);
  onDetectedRef.current = onDetected;
  onUnavailableRef.current = onUnavailable;

  useEffect(() => {
    if (!active) return;
    const video = videoRef.current;
    if (!video || typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      onUnavailableRef.current();
      return;
    }

    let stream: MediaStream | null = null;
    let timer: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;
    const reader = createReader();
    const canvas = document.createElement("canvas");
    let lastCode = "";
    let lastAt = 0;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } } })
      .then((s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        video.srcObject = s;
        return video.play();
      })
      .then(() => {
        if (cancelled) return;
        timer = setInterval(() => {
          if (video.readyState < 2 || video.videoWidth === 0) return;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext("2d", { willReadFrequently: true });
          if (!ctx) return;
          ctx.drawImage(video, 0, 0);
          const code = decodeImageData(reader, ctx.getImageData(0, 0, canvas.width, canvas.height));
          if (!code) return;
          const now = Date.now();
          if (code === lastCode && now - lastAt < LIMITS.SCAN_DEBOUNCE_MS) return;
          lastCode = code;
          lastAt = now;
          onDetectedRef.current(code);
        }, FRAME_INTERVAL_MS);
      })
      .catch(() => {
        if (!cancelled) onUnavailableRef.current();
      });

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
      stream?.getTracks().forEach((t) => t.stop());
      if (video) video.srcObject = null;
    };
  }, [active]);

  return (
    <div className="camera" data-testid="camera-preview">
      <video ref={videoRef} muted playsInline className="camera__video" />
      <div className="camera__label">{label}</div>
    </div>
  );
}
