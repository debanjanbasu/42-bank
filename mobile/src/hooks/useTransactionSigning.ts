import { useState, useCallback } from 'react';

export interface PendingTransaction {
  recipient: string;
  amount: number;
  note: string;
}

export function useTransactionSigning() {
  const [pendingTx, setPendingTx] = useState<PendingTransaction | null>(null);
  const [resolveRef, setResolveRef] = useState<((sig: string | null) => void) | null>(null);

  const requestSignature = useCallback(
    (tx: PendingTransaction): Promise<string | null> => {
      return new Promise((resolve) => {
        setPendingTx(tx);
        // Wrap in thunk so React doesn't call it as an updater function
        setResolveRef(() => resolve);
      });
    },
    [],
  );

  const handleConfirm = useCallback(
    (signature: string) => {
      setPendingTx(null);
      resolveRef?.(signature);
      setResolveRef(null);
    },
    [resolveRef],
  );

  const handleCancel = useCallback(() => {
    setPendingTx(null);
    resolveRef?.(null);
    setResolveRef(null);
  }, [resolveRef]);

  return { pendingTx, requestSignature, handleConfirm, handleCancel };
}
