/**
 * Title Generation (§1.11)
 *
 * Auto-generates concise session titles from first turn exchange.
 */

export function cleanTitle(raw: string): string {
  let t = raw.trim();
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    t = t.slice(1, -1).trim();
  }
  if (t.toLowerCase().startsWith("title:")) {
    t = t.slice(6).trim();
  }
  t = t.replace(/[.!?;:]+$/, "");
  if (t.length > 80) {
    t = t.slice(0, 77) + "...";
  }
  return t;
}

export function fallbackTitle(userMessage: string): string {
  const words = userMessage.trim().split(/\s+/).slice(0, 6);
  if (words.length === 0 || words[0] === "") {
    return "New Session";
  }
  const title = words.join(" ");
  return title.charAt(0).toUpperCase() + title.slice(1);
}

export class TitleGenerator {
  public generate(userMessage: string, assistantResponse: string = ""): string {
    return fallbackTitle(userMessage);
  }
}
