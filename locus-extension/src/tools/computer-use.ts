/**
 * locus-extension/src/tools/computer-use.ts - Computer Use TypeScript client.
 *
 * Implements Spec §20.1-20.2
 */

export interface ScreenDimensions {
  width: number;
  height: number;
}

export class ComputerUseClient {
  constructor(private dimensions: ScreenDimensions = { width: 1920, height: 1080 }) {}

  public isWithinScreen(x: number, y: number): boolean {
    return x >= 0 && x <= this.dimensions.width && y >= 0 && y <= this.dimensions.height;
  }
}
