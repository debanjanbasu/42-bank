import { useState, useCallback, useRef } from 'react';

export interface PendingTransaction {
recipient: string;
amount: number;
note: string;
}

export function useTransactionSigning() {
const [pendingTx, setPendingTx] = useState<PendingTransaction | null>(null);
const resolveRef = useRef<((sig: string | null) => void) | null>(null);

const requestSignature = useCallback(
(tx: PendingTransaction): Promise<string | null> => {
return new Promise((resolve) => {
setPendingTx(tx);
resolveRef.current = resolve;
});
},
[],
);

const handleConfirm = useCallback((signature: string) => {
setPendingTx(null);
if (resolveRef.current) {
resolveRef.current(signature);
resolveRef.current = null;
}
}, []);

const handleCancel = useCallback(() => {
setPendingTx(null);
if (resolveRef.current) {
resolveRef.current(null);
resolveRef.current = null;
}
}, []);

return { pendingTx, requestSignature, handleConfirm, handleCancel };
}
