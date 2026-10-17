// Bound initial evidence fan-out so one workspace cannot exhaust the API pool.
export function requestLimit(concurrency: number) {
  let active = 0;
  const waiting: Array<() => void> = [];
  return async function limited<T>(work: () => Promise<T>): Promise<T> {
    if (active >= concurrency) await new Promise<void>(resolve => waiting.push(resolve));
    else active++;
    try { return await work(); }
    finally {
      const next = waiting.shift();
      if (next) next();
      else active--;
    }
  };
}
