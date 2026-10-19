import { useEffect, useState } from "react";
import api from "../services/api";

export type HomePeriod = "jour" | "semaine" | "trimestre";

type Kpi = { id: string; value: number | null };
type Point = { trips: number };
type Dash = {
  kpis: Kpi[];
  timeseries: { points: Point[] };
};

type Props = {
  period: HomePeriod;
  people: number | null;
  refreshKey?: number;
};

const PERIOD_FACTOR: Record<HomePeriod, number> = {
  jour: 1,
  semaine: 5,
  trimestre: 65,
};

function num(value: number, digits = 0) {
  return value.toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function Delta({ ratio }: { ratio: number | null }) {
  if (ratio == null || !Number.isFinite(ratio)) return null;
  const pct = Math.round(ratio * 100);
  const up = pct >= 0;
  return (
    <span className={up ? "home-delta up" : "home-delta down"}>
      {up ? "↑" : "↓"} {Math.abs(pct)} % vs. période précédente
    </span>
  );
}

export default function HomeKpis({ period, people, refreshKey = 0 }: Props) {
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/kpi/dashboard")
      .then((res) => {
        if (!cancelled) {
          setData(res.data);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Indicateurs indisponibles. Vérifie que l'API est démarrée.");
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (error) return <p className="home-kpi-status">{error}</p>;
  if (!data) return <p className="home-kpi-status">Chargement des indicateurs…</p>;

  const byId = Object.fromEntries(data.kpis.map((item) => [item.id, item.value]));
  const factor = PERIOD_FACTOR[period];
  const trips = (byId.trips ?? 0) * factor;
  const km = (byId.km ?? 0) * factor;
  const avgMin = byId.time ?? 0;
  const hours = (trips * avgMin) / 60;
  const co2 = (byId.co2 ?? 0) * factor;
  const points = data.timeseries.points;
  const prev = points.length > 1 ? points[points.length - 2].trips : 0;
  const last = points.length ? points[points.length - 1].trips : 0;
  const ratio = prev > 0 ? (last - prev) / prev : null;

  const cards = [
    {
      key: "trips",
      label: "Nombre de trajets",
      value: num(trips),
      tone: "violet",
      delta: ratio,
      hint: null as string | null,
    },
    {
      key: "people",
      label: "Personnes uniques",
      value: people == null ? "—" : num(people),
      tone: "green",
      delta: null,
      hint: "Navettes simulées du cadre affiché",
    },
    {
      key: "km",
      label: "Distance totale",
      value: `${num(km, 1)} km`,
      tone: "orange",
      delta: ratio,
      hint: null,
    },
    {
      key: "hours",
      label: "Durée totale",
      value: `${num(hours)} h`,
      tone: "red",
      delta: ratio,
      hint: null,
    },
    {
      key: "co2",
      label: "Émissions estimées de CO₂",
      value: `${num(co2, 1)} t`,
      tone: "teal",
      delta: ratio,
      hint: null,
    },
  ];

  return (
    <>
      <div className="home-kpis">
        {cards.map((card) => (
          <article key={card.key} className="home-kpi">
            <span className={`home-kpi-ico ${card.tone}`} aria-hidden="true" />
            <span className="home-kpi-label">{card.label}</span>
            <strong>{card.value}</strong>
            {card.delta != null ? <Delta ratio={card.delta} /> : null}
            {card.hint ? <span className="home-kpi-hint">{card.hint}</span> : null}
          </article>
        ))}
      </div>
      <p className="home-kpi-note">
        Volumes d'une journée type, multipliés par 5 (semaine) ou 65 (trimestre). Les
        pourcentages reprennent la saisonnalité illustrative, pas un historique mesuré.
      </p>
    </>
  );
}
