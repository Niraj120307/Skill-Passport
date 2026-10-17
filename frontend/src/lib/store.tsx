import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, type Passport } from "./api";

const KEY = "skill-passport:current-id";

function readId(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}
function writeId(id: string | null) {
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable — the passport is still saved in the backend */
  }
}

interface Ctx {
  passportId: string | null;
  passport: Passport | null;
  loading: boolean;
  error: string | null;
  setPassport: (p: Passport) => void;
  selectPassport: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
  clear: () => void;
}

const PassportContext = createContext<Ctx | null>(null);

export function PassportProvider({ children }: { children: ReactNode }) {
  const [passportId, setPassportId] = useState<string | null>(readId);
  const [passport, setPassportState] = useState<Passport | null>(null);
  const [loading, setLoading] = useState<boolean>(!!readId());
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const p = await api.getPassport(id);
      setPassportState(p);
      setPassportId(p.id);
      writeId(p.id);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        writeId(null);
        setPassportId(null);
        setPassportState(null);
      } else {
        setError(e instanceof Error ? e.message : "Failed to load passport");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (passportId) void load(passportId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value: Ctx = {
    passportId,
    passport,
    loading,
    error,
    setPassport: (p) => {
      setPassportState(p);
      setPassportId(p.id);
      writeId(p.id);
    },
    selectPassport: load,
    refresh: async () => {
      if (passportId) await load(passportId);
    },
    clear: () => {
      writeId(null);
      setPassportId(null);
      setPassportState(null);
    },
  };
  return <PassportContext.Provider value={value}>{children}</PassportContext.Provider>;
}

export function usePassport() {
  const ctx = useContext(PassportContext);
  if (!ctx) throw new Error("usePassport must be used within PassportProvider");
  return ctx;
}
