/**
 * Generate a compact circle abbreviation from a party code.
 * Rules:
 *  - Max 4 real letters/digits shown.
 *  - Parentheses ( ) are included but NOT counted toward the 4-letter limit.
 *  - Stops at the first space, dash, or other separator.
 * Examples: CPI(M)→CPI(M)  JD(S)→JD(S)  IUML→IUML  IND (BJP)→IND
 */
export function partyAbbr(code: string): string {
  let result = '';
  let letterCount = 0;
  let inBracket = false;
  for (const ch of code) {
    if (/[A-Z0-9]/i.test(ch)) {
      if (letterCount >= 4) {
        if (inBracket) continue; // skip excess letters inside bracket, still need to close
        break;
      }
      result += ch;
      letterCount++;
    } else if (ch === '(') {
      if (letterCount >= 4) break;
      result += ch;
      inBracket = true;
    } else if (ch === ')') {
      result += ch;
      inBracket = false;
      if (letterCount >= 4) break;
    } else {
      break; // space, dash, or separator — stop
    }
  }
  return result.replace(/\($/, ''); // remove any trailing unclosed (
}
