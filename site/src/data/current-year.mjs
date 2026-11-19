export const currentYear = new Date().getUTCFullYear();

export function isInYear(value, year = currentYear) {
  if (value instanceof Date) return value.getUTCFullYear() === year;
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}(?:$|T)/.test(value)
    && new Date(value).getUTCFullYear() === year;
}

export function yearSnapshot(snapshot, year = currentYear) {
  return {
    generated_at: snapshot.generated_at,
    platform: snapshot.platform,
    sources: snapshot.sources ?? [],
    reports: (snapshot.reports ?? []).filter((row) => isInYear(row.published, year)),
    indicators: (snapshot.indicators ?? []).filter((row) => isInYear(row.valid_from ?? row.created_at, year)),
    series: (snapshot.series ?? []).filter((row) => isInYear(row.date, year)),
  };
}