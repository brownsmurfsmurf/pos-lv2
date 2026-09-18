"use client";
import { useMemo, useSyncExternalStore } from "react";
import { createCartStore, type CartState, type CartStore } from "./store";

export function useCartStore(): [CartState, CartStore] {
  const store = useMemo(() => createCartStore(), []);
  const state = useSyncExternalStore(
    store.subscribe,
    () => store.state,
    () => store.state,
  );
  return [state, store];
}
