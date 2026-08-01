/**
 * Citation marker parsing, kept in sync with the backend's
 * `services/generation/app/services/citation_extractor.py:CITATION_RX`.
 *
 * Models pad the marker with markdown emphasis (`[**SOURCE_2**]`) or invisible
 * characters such as U+200B between the bracket and the keyword. A pattern that
 * misses a variant costs the reader every citation in that answer, so both ends
 * stay permissive and identical.
 */
// The zero-width joiner sits outside the character class on purpose: inside one it
// reads as a grapheme-cluster combiner, whereas here each of these is simply one more
// invisible character to skip over.
const PAD = "(?:[\\s*_~`\\u200b\\u200c\\u2060\\ufeff]|\\u200d)*";

/** Fresh instance per call — a shared /g regex carries `lastIndex` between uses. */
export function sourceMarkerRegex(): RegExp {
  return new RegExp(`[\\[(【]${PAD}SOURCE${PAD}[-_\\s]?${PAD}(\\d+)${PAD}[\\])】]`, "gi");
}

/** Rewrite every marker variant to the plain `[n]` form used for display. */
export function normalizeCitationMarkers(text: string): string {
  return text.replace(sourceMarkerRegex(), "[$1]");
}

/** Highest source number cited so far — drives progressive citation reveal. */
export function highestCitedIndex(text: string): number {
  let highest = 0;
  // Both the raw `[SOURCE_n]` forms and the already-normalised `[n]` form.
  for (const m of text.matchAll(sourceMarkerRegex())) {
    highest = Math.max(highest, parseInt(m[1], 10));
  }
  for (const m of text.matchAll(/[[【]\s*(\d{1,3})\s*[\]】]/g)) {
    highest = Math.max(highest, parseInt(m[1], 10));
  }
  return highest;
}
