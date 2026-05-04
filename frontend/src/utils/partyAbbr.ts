/**
 * Converts a party code to its canonical display form.
 * Rules:
 *  - Underscores become bracket notation: CPI_M → CPI(M), IND_LDF → IND(LDF)
 *  - Parentheses from the original code are preserved: JD(S) stays JD(S)
 * Examples:
 *   CPI_M   → CPI(M)
 *   IND_LDF → IND(LDF)
 *   IND_UDF → IND(UDF)
 *   IUML    → IUML
 *   JD(S)   → JD(S)
 */
export function partyDisplay(code: string): string {
  // Convert first underscore to bracket notation: ABC_XYZ → ABC(XYZ)
  const underscoreIdx = code.indexOf('_');
  if (underscoreIdx !== -1) {
    const base = code.slice(0, underscoreIdx);
    const suffix = code.slice(underscoreIdx + 1);
    return `${base}(${suffix})`;
  }
  return code;
}

/**
 * Generate a compact circle badge abbreviation from a party code.
 * Rules:
 *  - First converts code via partyDisplay (underscores → brackets)
 *  - Max 4 real letters/digits shown.
 *  - Parentheses ( ) are included but NOT counted toward the 4-letter limit.
 *  - Stops at space or other separators.
 * Examples:
 *   CPI_M   → CPI(M)    (3 letters + bracket)
 *   IND_LDF → IND(LDF)  (3 + bracket with 3 — all shown since bracket chars don't count)
 *   IUML    → IUML       (4 letters)
 *   JD(S)   → JD(S)
 *   INC     → INC
 */
export function partyAbbr(code: string): string {
  // IND_* candidates: badge just shows IND — alliance context goes in text via partyDisplay
  if (code.startsWith('IND_')) return 'IND';
  // Normalize underscores to brackets first
  const display = partyDisplay(code);
  let result = '';
  let letterCount = 0;
  let inBracket = false;
  for (const ch of display) {
    if (/[A-Z0-9]/i.test(ch)) {
      if (!inBracket && letterCount >= 4) break; // stop at 4 outside brackets
      result += ch;
      if (!inBracket) letterCount++;
    } else if (ch === '(') {
      if (!inBracket && letterCount >= 4) break;
      result += ch;
      inBracket = true;
    } else if (ch === ')') {
      result += ch;
      inBracket = false;
    } else {
      break; // space or separator — stop
    }
  }
  return result.replace(/\($/, ''); // remove any trailing unclosed (
}
