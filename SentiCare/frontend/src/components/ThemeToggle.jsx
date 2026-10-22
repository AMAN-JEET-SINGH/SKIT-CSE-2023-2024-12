import { Moon, Sun } from "lucide-react";
import useTheme from "../contexts/useTheme";

export default function ThemeToggle({ compact = false }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const Icon = isDark ? Sun : Moon;
  const label = isDark ? "Light mode" : "Dark mode";

  return (
    <button
      type="button"
      className={`theme-toggle${compact ? " theme-toggle-compact" : ""}`}
      onClick={toggleTheme}
      aria-label={`Switch to ${label.toLowerCase()}`}
      aria-pressed={isDark}
      title={`Switch to ${label.toLowerCase()}`}
    >
      <Icon size={18} aria-hidden="true" />
    </button>
  );
}
