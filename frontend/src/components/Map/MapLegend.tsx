/** Légende Flux OD — calée sur le visuel projet. */
export default function MapLegend() {
  const items = [
    { color: "#dc2626", label: "> 200 déplacements" },
    { color: "#f97316", label: "150 – 200" },
    { color: "#eab308", label: "100 – 150" },
    { color: "#22c55e", label: "50 – 100" },
    { color: "#166534", label: "< 50" },
  ];

  return (
    <div className="map-legend-card">
      <h3>Flux OD</h3>
      <ul>
        {items.map((item) => (
          <li key={item.label}>
            <span className="legend-line" style={{ background: item.color }} />
            {item.label}
          </li>
        ))}
      </ul>
      <p className="legend-note">Volumes démo (échelle relative)</p>
    </div>
  );
}
