/**
 * locus-extension/src/state/redis-client.ts - Redis TypeScript client.
 *
 * Implements Spec §30.9
 */

export class RedisStateClient {
  constructor(private host: string = "localhost", private port: number = 6379) {}

  public getConnectionString(): string {
    return `redis://${this.host}:${this.port}`;
  }
}
