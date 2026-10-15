/**
 * Think Token Scrubber (§13.9)
 *
 * Strips <think>, <thinking>, <reasoning> blocks from streamed assistant text.
 */

export const SUPPORTED_TAGS = ["think", "thinking", "reasoning", "thought", "REASONING_SCRATCHPAD"];

export class ThinkTokenScrubber {
  public scrub(text: string): string {
    let result = text;
    for (const tag of SUPPORTED_TAGS) {
      const openTag = `<${tag}>`;
      const closeTag = `</${tag}>`;
      const regex = new RegExp(`${openTag}[\\s\\S]*?${closeTag}`, "gi");
      result = result.replace(regex, "");
    }
    return result.trim();
  }
}
