import { createContext, useContext, useState, useEffect } from "react";
import { Sun, Moon, Sparkles } from "lucide-react";

type Theme = "light" | "dark" | "glass";

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "light",
  setTheme: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("loanassist-theme");
      if (stored === "light" || stored === "dark" || stored === "glass") return stored;
    }
    return "glass";
  });

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark", "glass");

    if (theme === "dark") {
      root.classList.add("dark");
    } else if (theme === "glass") {
      root.classList.add("dark", "glass");
    }

    localStorage.setItem("loanassist-theme", theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const modes: { value: Theme; icon: typeof Sun; label: string }[] = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "glass", icon: Sparkles, label: "Glass" },
  ];

  return (
    <div
      data-testid="theme-toggle"
      className="flex items-center gap-0.5 p-1 rounded-2xl bg-gray-100 dark:bg-white/10 border border-gray-200/60 dark:border-white/10 shadow-sm"
    >
      {modes.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          data-testid={`theme-${value}`}
          onClick={() => setTheme(value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-medium transition-all duration-300 ${
            theme === value
              ? "bg-white dark:bg-white/20 text-gray-900 dark:text-white shadow-sm"
              : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          }`}
        >
          <Icon className="w-3 h-3" />
          {label}
        </button>
      ))}
    </div>
  );
}
