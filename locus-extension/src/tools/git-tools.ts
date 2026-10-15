/**
 * locus-extension/src/tools/git-tools.ts - Git Tools TypeScript client.
 *
 * Implements Spec §3.7a
 */

export interface GitOperationResult {
  command: string;
  exitCode: number;
  stdout: string;
  stderr: string;
  success: boolean;
}

export class GitToolClient {
  constructor(private repoPath: string = ".") {}

  public getRepoPath(): string {
    return this.repoPath;
  }

  public formatGitCommand(args: string[]): string {
    return `git ${args.join(" ")}`;
  }
}
