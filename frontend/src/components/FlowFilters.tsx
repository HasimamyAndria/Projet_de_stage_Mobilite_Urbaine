import type { OdFilters } from "../types";

type Props = {
  filters: OdFilters;
  onChange: (next: OdFilters) => void;
  compact?: boolean;
};

const MODES = [
  { id: "all", label: "Tous modes" },
  { id: "car", label: "Voiture" },
  { id: "bus", label: "Bus / TC" },
  { id: "bike", label: "Vélo" },
  { id: "walk", label: "Marche" },
];

const DAYS = [
  { id: null, label: "Semaine type" },
  { id: 1, label: "Lun" },
  { id: 2, label: "Mar" },
  { id: 3, label: "Mer" },
  { id: 4, label: "Jeu" },
  { id: 5, label: "Ven" },
  { id: 6, label: "Sam" },
  { id: 7, label: "Dim" },
];

export default function FlowFilters({ filters, onChange, compact }: Props) {
  return (
    <div className={compact ? "flow-filters compact" : "flow-filters"}>
      <label>
        Mode
        <select
          value={filters.mode}
          onChange={(e) => onChange({ ...filters, mode: e.target.value })}
        >
          {MODES.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Jour
        <select
          value={filters.weekday ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              weekday: e.target.value === "" ? null : Number(e.target.value),
            })
          }
        >
          {DAYS.map((d) => (
            <option key={String(d.id)} value={d.id ?? ""}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Seuil volume
        <input
          type="range"
          min={5}
          max={80}
          value={filters.minPassengers}
          onChange={(e) =>
            onChange({ ...filters, minPassengers: Number(e.target.value) })
          }
        />
        <span>{filters.minPassengers}</span>
      </label>
    </div>
  );
}
