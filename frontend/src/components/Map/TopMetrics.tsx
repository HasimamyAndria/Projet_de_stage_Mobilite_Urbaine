type Props = {
  zones: number | null;
  flowCount: number | null;
  corridors: number | null;
  ehAvg: number | null;
  loading?: boolean;
  labels?: [string, string, string, string];
};

export default function TopMetrics({
  zones,
  flowCount,
  corridors,
  ehAvg,
  loading,
  labels,
}: Props) {
  const dash = loading ? "…" : "—";
  const [zonesLabel, flowsLabel, corridorsLabel, ehLabel] = labels ?? [
    "Zones OD",
    "Flux OD agrégés",
    "Corridors M2",
    "Indice emploi-habitat",
  ];
  return (
    <div className="metrics-row">
      <div className="metric-card teal">
        <span className="label">{zonesLabel}</span>
        <span className="value">{zones ?? dash}</span>
      </div>
      <div className="metric-card orange">
        <span className="label">{flowsLabel}</span>
        <span className="value">
          {flowCount != null ? flowCount.toLocaleString("fr-FR") : dash}
        </span>
      </div>
      <div className="metric-card red">
        <span className="label">{corridorsLabel}</span>
        <span className="value">{corridors ?? dash}</span>
      </div>
      <div className="metric-card blue">
        <span className="label">{ehLabel}</span>
        <span className="value">{ehAvg ?? dash}</span>
      </div>
    </div>
  );
}
