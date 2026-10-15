/**
 * Locus QLoRA Fine-Tuning Pipeline (§30.6 / §30.7) TypeScript companion.
 */

export interface TrainingSample {
  sampleId: string;
  instruction: string;
  inputContext: string;
  output: string;
  sourceType: string;
  qualityScore: number;
}

export class QLoRADatasetCurator {
  private samples: TrainingSample[] = [];

  constructor(public minQualityThreshold: number = 0.75) {}

  addSample(
    sampleId: string,
    instruction: string,
    inputContext: string,
    output: string,
    qualityScore: number = 0.9
  ): TrainingSample | null {
    if (qualityScore < this.minQualityThreshold) return null;
    const sample: TrainingSample = {
      sampleId,
      instruction,
      inputContext,
      output,
      sourceType: 'trajectory_success',
      qualityScore,
    };
    this.samples.push(sample);
    return sample;
  }

  exportAlpaca(): Array<{ instruction: string; input: string; output: string }> {
    return this.samples.map((s) => ({
      instruction: s.instruction,
      input: s.inputContext,
      output: s.output,
    }));
  }
}
