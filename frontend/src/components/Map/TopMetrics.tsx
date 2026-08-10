type Props = {
  zones: number | null;
  flowCount: number | null;
  corridors: number | null;
  ehAvg: number | null;
  loading?: boolean;
};

export default function TopMetrics({
  zones,
  flowCount,
  corridors,
  ehAvg,
  loading,
}: Props) {
  const dash = loading ? "…" : "—";
  return (
    <div className="metrics-row">
      <div className="metric-card teal">
        <span className="label">Zones OD</span>
        <span className="value">{zones ?? dash}</span>
      </div>
      <div className="metric-card orange">
        <span className="label">Flux OD agrégés</span>
        <span className="value">
          {flowCount != null ? flowCount.toLocaleString("fr-FR") : dash}
        </span>
      </div>
      <div className="metric-card red">
        <span className="label">Corridors M2</span>
        <span className="value">{corridors ?? dash}</span>
      </div>
      <div className="metric-card blue">
        <span className="label">Indice emploi-habitat</span>
        <span className="value">{ehAvg ?? dash}</span>
      </div>
    </div>
  );
}
