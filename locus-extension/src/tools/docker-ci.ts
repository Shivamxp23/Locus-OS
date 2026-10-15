/**
 * locus-extension/src/tools/docker-ci.ts - Docker CI TypeScript client.
 *
 * Implements Spec §23.1-23.5
 */

export class DockerCiClient {
  public static getKnownServices(): string[] {
    return ["locus-couchdb", "locus-neo4j", "locus-postgres", "locus-qdrant", "locus-sidecar"];
  }
}
