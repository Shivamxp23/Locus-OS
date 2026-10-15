/**
 * Holographic Reduced Representations (HRR) (§4.10)
 *
 * Ephemeral situational state binding and vector unbinding.
 */

export interface HRRVector {
  values: number[];
  dim: number;
}

export class Codebook {
  public symbols: Map<string, HRRVector> = new Map();
  public dim: number;

  constructor(dim: number = 512) {
    this.dim = dim;
  }

  public getOrCreate(symbol: string): HRRVector {
    let vec = this.symbols.get(symbol);
    if (!vec) {
      const vals: number[] = [];
      const scale = 1.0 / Math.sqrt(this.dim);
      let normSq = 0;
      for (let i = 0; i < this.dim; i++) {
        // Box-Muller approx or uniform normal
        const u = Math.random();
        const v = Math.random();
        const z = Math.sqrt(-2.0 * Math.log(u || 1e-7)) * Math.cos(2.0 * Math.PI * v);
        const val = z * scale;
        vals.push(val);
        normSq += val * val;
      }
      const norm = Math.sqrt(normSq) || 1.0;
      const normalized = vals.map(v => v / norm);
      vec = { values: normalized, dim: this.dim };
      this.symbols.set(symbol, vec);
    }
    return vec;
  }
}

export function circularConvolution(a: number[], b: number[]): number[] {
  const n = a.length;
  const c = new Array(n).fill(0);
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const k = (i + j) % n;
      c[k] += a[i] * b[j];
    }
  }
  // Normalize
  let normSq = 0;
  for (let i = 0; i < n; i++) normSq += c[i] * c[i];
  const norm = Math.sqrt(normSq) || 1.0;
  return c.map(v => v / norm);
}

export function circularCorrelation(c: number[], b: number[]): number[] {
  const n = b.length;
  const bInv = new Array(n);
  for (let i = 0; i < n; i++) {
    bInv[i] = b[(n - i) % n];
  }
  return circularConvolution(c, bInv);
}

export function cosineSimilarity(v1: number[], v2: number[]): number {
  let dot = 0;
  let n1Sq = 0;
  let n2Sq = 0;
  for (let i = 0; i < v1.length; i++) {
    dot += v1[i] * v2[i];
    n1Sq += v1[i] * v1[i];
    n2Sq += v2[i] * v2[i];
  }
  const denom = Math.sqrt(n1Sq) * Math.sqrt(n2Sq);
  return denom > 1e-12 ? dot / denom : 0;
}

export class HolographicMemory {
  private codebook: Codebook;
  private storedStates: Map<string, HRRVector> = new Map();

  constructor(dim: number = 512) {
    this.codebook = new Codebook(dim);
  }

  public storeState(
    stateId: string,
    currentTask: string,
    activeMode: string,
    stressLevel: string
  ): HRRVector {
    const kTask = this.codebook.getOrCreate("KEY_TASK");
    const vTask = this.codebook.getOrCreate(`TASK:${currentTask}`);
    const pairTask = circularConvolution(kTask.values, vTask.values);

    const kMode = this.codebook.getOrCreate("KEY_MODE");
    const vMode = this.codebook.getOrCreate(`MODE:${activeMode}`);
    const pairMode = circularConvolution(kMode.values, vMode.values);

    const kStress = this.codebook.getOrCreate("KEY_STRESS");
    const vStress = this.codebook.getOrCreate(`STRESS:${stressLevel}`);
    const pairStress = circularConvolution(kStress.values, vStress.values);

    const n = kTask.dim;
    const bundle = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      bundle[i] = pairTask[i] + pairMode[i] + pairStress[i];
    }
    let normSq = 0;
    for (let i = 0; i < n; i++) normSq += bundle[i] * bundle[i];
    const norm = Math.sqrt(normSq) || 1.0;
    const finalVec: HRRVector = {
      values: bundle.map(v => v / norm),
      dim: n,
    };
    this.storedStates.set(stateId, finalVec);
    return finalVec;
  }

  public queryStateAttribute(stateId: string, keyName: string): string | null {
    const state = this.storedStates.get(stateId);
    if (!state) return null;
    const keyVec = this.codebook.getOrCreate(`KEY_${keyName.toUpperCase()}`);
    const noisy = circularCorrelation(state.values, keyVec.values);

    let bestSymbol: string | null = null;
    let maxSim = -1.0;
    for (const [sym, proto] of this.codebook.symbols.entries()) {
      const sim = cosineSimilarity(noisy, proto.values);
      if (sim > maxSim && sim >= 0.25) {
        maxSim = sim;
        bestSymbol = sym;
      }
    }
    if (bestSymbol && bestSymbol.includes(":")) {
      return bestSymbol.split(":")[1];
    }
    return bestSymbol;
  }
}
