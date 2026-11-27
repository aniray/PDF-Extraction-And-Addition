export function parseRange(value, count) {
  if (!value.trim()) return Array.from({ length: count }, (_, i) => i + 1);
  const result = [];
  for (const token of value.split(',')) {
    const match = token.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) throw new Error('Use page numbers or ranges, for example 1-3, 5.');
    const start = Number(match[1]), end = Number(match[2] ?? match[1]);
    if (start < 1 || end > count || end < start) throw new Error(`Choose pages between 1 and ${count}, with ranges in ascending order.`);
    for (let number = start; number <= end; number++) {
      if (!result.includes(number)) result.push(number);
    }
  }
  return result;
}

export function movePage(pages, from, to) {
  const result = [...pages];
  if (from < 0 || to < 0 || from >= result.length || to >= result.length) return result;
  result.splice(to, 0, result.splice(from, 1)[0]);
  return result;
}
