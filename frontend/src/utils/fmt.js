const nf = new Intl.NumberFormat('pt-BR')
export const fmtInt = (n) => nf.format(Math.round(n || 0))
export const fmtPct = (x, d = 1) =>
  (x ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }) + '%'
export const fmtProb = (p) => (p == null ? '–' : p >= 0.995 ? '>99%' : p < 0.005 ? '<1%' : Math.round(p * 100) + '%')
export const ago = (ms) => {
  const s = Math.max(0, Math.round((Date.now() - ms) / 1000))
  return s < 2 ? 'agora' : s < 60 ? `há ${s}s` : `há ${Math.round(s / 60)} min`
}
