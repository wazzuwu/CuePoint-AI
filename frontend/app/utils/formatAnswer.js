export function fmtTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function stripChunkLabels(text) {
  return text.replace(/\[Chunk \d{4} — \d+:\d+(?::\d+)?\]\s*/g, '');
}
