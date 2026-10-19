import type { NavIconName } from "./stageViews";

type Props = { name: NavIconName };

export default function NavIcon({ name }: Props) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "home") {
    return (
      <svg {...common}>
        <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" />
      </svg>
    );
  }
  if (name === "map") {
    return (
      <svg {...common}>
        <path d="M9 4 4 6v14l5-2 6 2 5-2V4l-5 2-6-2z" />
        <path d="M9 4v14M15 6v14" />
      </svg>
    );
  }
  if (name === "chart") {
    return (
      <svg {...common}>
        <path d="M4 19V5M4 19h16" />
        <path d="M8 16v-5M12 16V8M16 16v-3" />
      </svg>
    );
  }
  if (name === "route") {
    return (
      <svg {...common}>
        <circle cx="6" cy="6" r="2" />
        <circle cx="18" cy="18" r="2" />
        <path d="M8 7c4 0 4 5 8 5h2M8 17c4 0 4-5 8-5" />
      </svg>
    );
  }
  if (name === "alert") {
    return (
      <svg {...common}>
        <path d="M12 4 3 19h18L12 4z" />
        <path d="M12 10v4M12 17h.01" />
      </svg>
    );
  }
  if (name === "balance") {
    return (
      <svg {...common}>
        <path d="M12 4v16M8 20h8M12 7l-5 6h10L12 7z" />
        <path d="M5 13h4M15 13h4" />
      </svg>
    );
  }
  if (name === "sliders") {
    return (
      <svg {...common}>
        <path d="M4 8h16M4 16h16" />
        <circle cx="9" cy="8" r="2" fill="currentColor" stroke="none" />
        <circle cx="15" cy="16" r="2" fill="currentColor" stroke="none" />
      </svg>
    );
  }
  if (name === "spark") {
    return (
      <svg {...common}>
        <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
      </svg>
    );
  }
  if (name === "steps") {
    return (
      <svg {...common}>
        <path d="M5 6h4v4H5zM15 14h4v4h-4z" />
        <path d="M9 8h6M11 8v6h4" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
      <path d="M14 3v5h5M8 13h8M8 17h6" />
    </svg>
  );
}
