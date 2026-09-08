import { useEffect, useRef } from "react";

type Props = {
  hour: number | null;
  playing: boolean;
  onHour: (hour: number | null) => void;
  onPlaying: (playing: boolean) => void;
};

export default function HourAnimator({ hour, playing, onHour, onPlaying }: Props) {
  const hourRef = useRef(hour);

  useEffect(() => {
    hourRef.current = hour;
  }, [hour]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const current = hourRef.current ?? -1;
      onHour((current + 1) % 24);
    }, 700);
    return () => window.clearInterval(id);
  }, [playing, onHour]);

  const label = hour == null ? "24 h" : `${String(hour).padStart(2, "0")} h`;

  return (
    <div className="hour-animator">
      <button
        type="button"
        className="map-btn"
        onClick={() => onPlaying(!playing)}
      >
        {playing ? "Pause" : "Animer 24 h"}
      </button>
      <input
        type="range"
        min={0}
        max={23}
        value={hour ?? 8}
        onChange={(e) => {
          onPlaying(false);
          onHour(Number(e.target.value));
        }}
        aria-label="Heure de la journée"
      />
      <strong>{label}</strong>
      <button
        type="button"
        className="map-btn"
        onClick={() => {
          onPlaying(false);
          onHour(null);
        }}
      >
        Journée
      </button>
    </div>
  );
}
