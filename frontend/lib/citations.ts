/**
 * Citation marker parsing, kept in sync with the backend's
 * `services/generation/app/services/citation_extractor.py:CITATION_RX`.
 *
 * Models pad the marker with markdown emphasis (`[**SOURCE_2**]`) or invisible
 * characters such as U+200B, and they group several references into one bracket
 * (`[SOURCE_3, SOURCE_5]`, sometimes `[SOURCE_3, 5]`). A pattern that misses a
 * variant costs the reader every citation in that bracket, so both ends stay
 * permissive and identical.
 */
// The zero-width joiner sits outside the character class on purpose: inside one it
// reads as a grapheme-cluster combiner, whereas here each of these is simply one more
// invisible character to skip over.
const PAD = "(?:[\\s*_~`\\u200b\\u200c\\u2060\\ufeff]|\\u200d)*";
/**
 * Answering in another language, models translate the marker despite the prompt
 * ("[ŹRÓDŁO 3]" instead of "[SOURCE_3]"). The prompt pins it; these catch the rest.
 */
const KEYWORD = "(?:SOURCE|ŹRÓDŁO|ZRODLO|ŹRODLO|QUELLE|FUENTE)";
/** One `SOURCE_n` reference, however the model chose to punctuate it. */
const ONE = `${KEYWORD}${PAD}[-_\\s]?${PAD}\\d+`;
/** What may sit between grouped references: `, ` `; ` ` and ` `&` `+` `/`. */
const SEP = `${PAD}(?:[,;&+/]|and)?${PAD}`;

/** Fresh instance per call — a shared /g regex carries `lastIndex` between uses. */
export function sourceMarkerRegex(): RegExp {
  return new RegExp(
    `[\\[(【]${PAD}${ONE}(?:${SEP}(?:${ONE}|\\d+))*${PAD}[\\])】]`,
    "gi"
  );
}

/**
 * Rewrite every marker variant to the plain `[n]` form used for display,
 * splitting a grouped bracket into one `[n]` per reference so each renders as
 * its own clickable chip.
 */
export function normalizeCitationMarkers(text: string): string {
  return text.replace(sourceMarkerRegex(), (marker) =>
    (marker.match(/\d+/g) ?? []).map((n) => `[${n}]`).join("")
  );
}

/** Highest source number cited so far — drives progressive citation reveal. */
export function highestCitedIndex(text: string): number {
  let highest = 0;
  // Both the raw `[SOURCE_n]` forms and the already-normalised `[n]` form.
  for (const marker of text.match(sourceMarkerRegex()) ?? []) {
    for (const n of marker.match(/\d+/g) ?? []) {
      highest = Math.max(highest, parseInt(n, 10));
    }
  }
  for (const m of text.matchAll(/[[【]\s*(\d{1,3})\s*[\]】]/g)) {
    highest = Math.max(highest, parseInt(m[1], 10));
  }
  return highest;
}
