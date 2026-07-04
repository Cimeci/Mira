"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * Shared flow state. The prototype is one state machine split across routes;
 * this preserves only the pieces that genuinely cross screens. The most
 * important is `mandateSigned`, which gates the facial-signature screen
 * (matching the original `goTo(4)` redirect-to-mandate-if-unsigned logic).
 */
export interface FlowState {
  urls: string[];
  discovery: number; // selected chip index
  actions: [boolean, boolean, boolean];
  mandateSigned: boolean;
  signatureStamp: string;
}

interface FlowContextValue extends FlowState {
  setUrls: (urls: string[]) => void;
  setDiscovery: (index: number) => void;
  setActions: (actions: [boolean, boolean, boolean]) => void;
  signMandate: (stamp: string) => void;
}

const FlowContext = createContext<FlowContextValue | null>(null);

export function FlowProvider({ children }: { children: ReactNode }) {
  const [urls, setUrls] = useState<string[]>([""]);
  const [discovery, setDiscovery] = useState(0);
  const [actions, setActions] = useState<[boolean, boolean, boolean]>([
    true,
    true,
    true,
  ]);
  const [mandateSigned, setMandateSigned] = useState(false);
  const [signatureStamp, setSignatureStamp] = useState("");

  const signMandate = useCallback((stamp: string) => {
    setMandateSigned(true);
    setSignatureStamp(stamp);
  }, []);

  const value = useMemo<FlowContextValue>(
    () => ({
      urls,
      discovery,
      actions,
      mandateSigned,
      signatureStamp,
      setUrls,
      setDiscovery,
      setActions,
      signMandate,
    }),
    [urls, discovery, actions, mandateSigned, signatureStamp, signMandate]
  );

  return <FlowContext.Provider value={value}>{children}</FlowContext.Provider>;
}

export function useFlow(): FlowContextValue {
  const ctx = useContext(FlowContext);
  if (!ctx) throw new Error("useFlow must be used within a FlowProvider");
  return ctx;
}
