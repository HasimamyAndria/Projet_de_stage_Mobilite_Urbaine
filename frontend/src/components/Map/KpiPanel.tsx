import { useEffect, useState } from "react";
import api from "../../services/api";
import "./KpiPanel.css";

type TopFlow = {
    origin_name: string;
    destination_name: string;
    passenger_count: number;
    average_distance_km: number | null;
    average_time_min: number | null;
};

type OdSummary = {
    zones: number;
    flow_count: number;
    total_passengers: number;
    max_flow: number;
    avg_flow: number;
    top_flows: TopFlow[];
    synthetic: boolean;
    note: string;
};

type KeypointCounts = {
    dormitory: number;
    employment: number;
    balanced: number;
    corridors: number;
};

type KeypointsPayload = {
    counts: KeypointCounts;
    rules: Record<string, string | number>;
    note: string;
    synthetic: boolean;
    clustering?: {
        method: string;
        k: number;
        silhouette: number;
        note: string;
    };
};

type EmploiHabitatSummary = {
    zone_count: number;
    scored_count: number;
    avg_score: number | null;
    min_score: number | null;
    max_score: number | null;
    min_zone_name: string | null;
    max_zone_name: string | null;
};

type EmploiHabitatPayload = {
    summary: EmploiHabitatSummary;
    formula: string;
    note: string;
    synthetic: boolean;
};

export type KpiMetrics = {
    zones: number | null;
    flowCount: number | null;
    corridors: number | null;
    ehAvg: number | null;
    loading: boolean;
};

type Props = {
    onMetrics?: (metrics: KpiMetrics) => void;
    refreshKey?: number;
};

export default function KpiPanel({ onMetrics, refreshKey = 0 }: Props) {
    const [summary, setSummary] = useState<OdSummary | null>(null);
    const [keypoints, setKeypoints] = useState<KeypointsPayload | null>(null);
    const [emploiHabitat, setEmploiHabitat] =
        useState<EmploiHabitatPayload | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadPanelData() {
            setLoading(true);
            onMetrics?.({
                zones: null,
                flowCount: null,
                corridors: null,
                ehAvg: null,
                loading: true,
            });
            setError(null);

            try {
                const summaryRes = await api.get("/api/od/summary", {
                    params: { top_n: 5 },
                });
                setSummary(summaryRes.data);

                const keyRes = await api.get("/api/keypoints", {
                    params: { corridor_top_n: 5 },
                });
                setKeypoints(keyRes.data);

                const ehRes = await api.get("/api/emploi-habitat");
                setEmploiHabitat(ehRes.data);

                onMetrics?.({
                    zones: summaryRes.data.zones ?? null,
                    flowCount: summaryRes.data.flow_count ?? null,
                    corridors: keyRes.data.counts?.corridors ?? null,
                    ehAvg: ehRes.data.summary?.avg_score ?? null,
                    loading: false,
                });
            } catch (err) {
                console.error("Erreur chargement panneau :", err);
                setError(
                    "Impossible de charger les indicateurs. Vérifie le backend (port 8000)."
                );
                onMetrics?.({
                    zones: null,
                    flowCount: null,
                    corridors: null,
                    ehAvg: null,
                    loading: false,
                });
            } finally {
                setLoading(false);
            }
        }

        loadPanelData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    if (loading) {
        return (
            <aside className="kpi-panel">
                <h2>Zones &amp; flux</h2>
                <p className="kpi-muted">Chargement des KPI…</p>
            </aside>
        );
    }

    if (error || !summary) {
        return (
            <aside className="kpi-panel">
                <h2>Zones &amp; flux</h2>
                <p className="kpi-error">{error ?? "Aucune donnée"}</p>
            </aside>
        );
    }

    return (
        <aside className="kpi-panel">
            <h2>Zones clés &amp; flux</h2>
            <p className="kpi-subtitle">Lecture décideur · M2 / M5 / M6</p>

            <section className="kpi-section">
                <h3>Synthèse</h3>
                <div className="kpi-grid">
                    <div className="kpi-card">
                        <span className="kpi-label">Zones</span>
                        <span className="kpi-value">{summary.zones}</span>
                    </div>
                    <div className="kpi-card">
                        <span className="kpi-label">Flux OD</span>
                        <span className="kpi-value">{summary.flow_count}</span>
                    </div>
                    <div className="kpi-card">
                        <span className="kpi-label">Volume total</span>
                        <span className="kpi-value">
                            {summary.total_passengers.toLocaleString("fr-FR")}
                        </span>
                    </div>
                    <div className="kpi-card">
                        <span className="kpi-label">Flux max</span>
                        <span className="kpi-value">{summary.max_flow}</span>
                    </div>
                </div>
            </section>

            {emploiHabitat && (
                <section className="kpi-section">
                    <h3>Emploi-habitat (M6)</h3>
                    <div className="kpi-grid">
                        <div className="kpi-card kpi-card-eh">
                            <span className="kpi-label">Score moyen</span>
                            <span className="kpi-value">
                                {emploiHabitat.summary.avg_score ?? "—"}
                            </span>
                        </div>
                        <div className="kpi-card">
                            <span className="kpi-label">Zones scorées</span>
                            <span className="kpi-value">
                                {emploiHabitat.summary.scored_count}
                            </span>
                        </div>
                        <div className="kpi-card kpi-card-eh-min">
                            <span className="kpi-label">Min (déséquilibré)</span>
                            <span className="kpi-value">
                                {emploiHabitat.summary.min_score ?? "—"}
                            </span>
                        </div>
                        <div className="kpi-card kpi-card-eh-max">
                            <span className="kpi-label">Max (équilibré)</span>
                            <span className="kpi-value">
                                {emploiHabitat.summary.max_score ?? "—"}
                            </span>
                        </div>
                    </div>
                    <p className="kpi-muted">
                        Min : {emploiHabitat.summary.min_zone_name ?? "—"}
                        {" · "}
                        Max : {emploiHabitat.summary.max_zone_name ?? "—"}
                    </p>
                </section>
            )}

            {keypoints && (
                <section className="kpi-section">
                    <h3>Points clés (M2)</h3>
                    <div className="kpi-grid">
                        <div className="kpi-card kpi-card-dorm">
                            <span className="kpi-label">Dortoirs</span>
                            <span className="kpi-value">
                                {keypoints.counts.dormitory}
                            </span>
                        </div>
                        <div className="kpi-card kpi-card-job">
                            <span className="kpi-label">Pôles emploi</span>
                            <span className="kpi-value">
                                {keypoints.counts.employment}
                            </span>
                        </div>
                        <div className="kpi-card">
                            <span className="kpi-label">Zones mixtes</span>
                            <span className="kpi-value">
                                {keypoints.counts.balanced}
                            </span>
                        </div>
                        <div className="kpi-card kpi-card-corridor">
                            <span className="kpi-label">Corridors</span>
                            <span className="kpi-value">
                                {keypoints.counts.corridors}
                            </span>
                        </div>
                    </div>
                    {keypoints.clustering && (
                        <p className="kpi-muted">
                            K-means k={keypoints.clustering.k}
                            {Number.isFinite(keypoints.clustering.silhouette)
                                ? ` · silhouette ${keypoints.clustering.silhouette}`
                                : ""}
                        </p>
                    )}
                </section>
            )}

            <section className="kpi-section">
                <h3>Top 5 desire lines</h3>
                <p className="kpi-muted">
                    Plus gros volumes zone → zone (pas des itinéraires rue)
                </p>
                <ol className="kpi-top-list">
                    {summary.top_flows.map((flow, index) => (
                        <li
                            key={`${flow.origin_name}-${flow.destination_name}-${index}`}
                        >
                            <div className="kpi-top-main">
                                <strong>
                                    {flow.origin_name} → {flow.destination_name}
                                </strong>
                                <span className="kpi-badge">
                                    {flow.passenger_count}
                                </span>
                            </div>
                            <div className="kpi-top-meta">
                                {flow.average_distance_km != null && (
                                    <span>{flow.average_distance_km} km</span>
                                )}
                                {flow.average_time_min != null && (
                                    <span>~{flow.average_time_min} min</span>
                                )}
                            </div>
                        </li>
                    ))}
                </ol>
            </section>

            <section className="kpi-note">
                <strong>
                    {summary.synthetic ? "Données synthétiques" : "Données réelles"}
                </strong>
                <p>{summary.note}</p>
            </section>
        </aside>
    );
}
