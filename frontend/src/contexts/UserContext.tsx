'use client';

/**
 * 全域使用者 Context
 * 提供 user 資訊 + hasPermission(module, action) 工具
 */
import { createContext, useContext, type ReactNode } from 'react';
import type { UserMe } from '@/types';

interface UserContextValue {
  user: UserMe | null;
  hasPermission: (module: string, action: string) => boolean;
}

const UserContext = createContext<UserContextValue>({
  user: null,
  hasPermission: () => false,
});

export function UserProvider({
  user,
  children,
}: {
  user: UserMe | null;
  children: ReactNode;
}) {
  const hasPermission = (module: string, action: string): boolean => {
    if (!user) return false;
    return user.permissions.includes(`${module}:${action}`);
  };

  return (
    <UserContext.Provider value={{ user, hasPermission }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  return useContext(UserContext);
}
