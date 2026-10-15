/**
 * locus-extension/src/tools/desktop-vnc.ts - VNC Remote Desktop TypeScript client.
 *
 * Implements Spec §20.3
 */

export class VncDesktopClient {
  constructor(private host: string = "localhost", private port: number = 5900) {}

  public getEndpoint(): string {
    return `${this.host}:${this.port}`;
  }
}
