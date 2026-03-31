'use client';

/**
 * Toast 通知系統 — 基於 Sonner
 * 保留原有 useToast() / showToast() API，不需修改各頁面呼叫點
 */
import { createContext, useContext, useCallback, type ReactNode } from 'react';
import { toast } from 'sonner';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const showToast = useCallback((message: string, type: ToastType = 'success') => {
    switch (type) {
      case 'success': toast.success(message); break;
      case 'error':   toast.error(message);   break;
      case 'warning': toast.warning(message); break;
      case 'info':    toast.info(message);    break;
    }
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
