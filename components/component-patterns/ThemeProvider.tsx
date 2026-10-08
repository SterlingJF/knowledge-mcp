import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light" | "system";

export type ThemeMode = Theme;

export type ResolvedThemeMode = "dark" | "light";

const COLOR_SCHEME_QUERY = "(prefers-color-scheme: dark)";

function systemColorScheme(): ResolvedThemeMode {
  if (
    typeof window === "undefined" ||
    typeof window.matchMedia !== "function"
  ) {
    return "light";
  }
  return window.matchMedia(COLOR_SCHEME_QUERY).matches ? "dark" : "light";
}

export type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
};

export type ThemeProviderState = {
  theme: Theme;
  resolvedTheme: ResolvedThemeMode;
  setTheme: (theme: Theme) => void;
};

const ThemeProviderContext = createContext<ThemeProviderState | undefined>(
  undefined,
);

export function ThemeProvider({
  children,
  defaultTheme = "system",
  storageKey = "vite-ui-theme",
  ...props
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(storageKey) as Theme | null) ?? defaultTheme,
  );

  const [systemTheme, setSystemTheme] =
    useState<ResolvedThemeMode>(systemColorScheme);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      return;
    }

    const query = window.matchMedia(COLOR_SCHEME_QUERY);
    const handleChange = (event: MediaQueryListEvent) =>
      setSystemTheme(event.matches ? "dark" : "light");

    setSystemTheme(query.matches ? "dark" : "light");
    query.addEventListener("change", handleChange);

    return () => query.removeEventListener("change", handleChange);
  }, []);

  const resolvedTheme: ResolvedThemeMode =
    theme === "system" ? systemTheme : theme;

  useEffect(() => {
    const root = window.document.documentElement;

    root.classList.remove("light", "dark");
    root.classList.add(resolvedTheme);
  }, [resolvedTheme]);

  const value = {
    theme,
    resolvedTheme,
    setTheme: (theme: Theme) => {
      localStorage.setItem(storageKey, theme);
      setTheme(theme);
    },
  };

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext);

  if (context === undefined)
    throw new Error("useTheme must be used within a ThemeProvider");

  return context;
};
