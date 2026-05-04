// ─────────────────────────────────────────────────────────────────────────────
// shareCard.ts — HTML5 Canvas share-card generator
// Draws a constituency result card at 2K resolution (1080×1920 or 1080×1350)
// and returns it as a PNG Blob for download.
// ─────────────────────────────────────────────────────────────────────────────

export type ShareFormat = '9:16' | '4:5';

export type ShareCardData = {
  constituencyName: string;
  constituencyNumber: number;
  district: string;
  leaderName: string;
  leaderParty: string;
  leaderAlliance: 'LDF' | 'UDF' | 'NDA' | 'OTH';
  leaderVotes: number;
  leaderPct: number;
  margin: number | null;
  runnerUpName: string | null;
  runnerUpParty: string | null;
  runnerUpAlliance: string | null;
  runnerUpVotes: number;
  runnerUpPct: number;
  otherCandidates: Array<{ name: string; party: string; alliance: string; votes: number; pct: number }>;
  status: string;
  countingPct: number;
  sittingAlliance: string | null;
  isFlip: boolean;
};

// ── Dimensions ────────────────────────────────────────────────────────────────
const FORMATS: Record<ShareFormat, { w: number; h: number }> = {
  '9:16': { w: 1080, h: 1920 },
  '4:5':  { w: 1080, h: 1350 },
};

// ── Alliance colours ──────────────────────────────────────────────────────────
const BG_GRADIENTS: Record<string, [string, string]> = {
  LDF: ['#7B0000', '#1A0505'],
  UDF: ['#003A6B', '#020D1A'],
  NDA: ['#7A3800', '#1A0B00'],
  OTH: ['#2D2D2D', '#0A0A0A'],
};

const ALLIANCE_ACCENT: Record<string, string> = {
  LDF: '#E05252',
  UDF: '#4BA8F0',
  NDA: '#F7A84B',
  OTH: '#9CA3AF',
};

const ALLIANCE_LABEL_BG: Record<string, string> = {
  LDF: '#D42B2B',
  UDF: '#1A8FE3',
  NDA: '#F7921C',
  OTH: '#6B7280',
};

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function accent(alliance: string): string {
  return ALLIANCE_ACCENT[alliance] ?? '#9CA3AF';
}

function labelBg(alliance: string): string {
  return ALLIANCE_LABEL_BG[alliance] ?? '#6B7280';
}

/** Truncate text to fit within maxWidth, appending … if needed */
function fitText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let t = text;
  while (t.length > 0 && ctx.measureText(t + '…').width > maxWidth) {
    t = t.slice(0, -1);
  }
  return t + '…';
}

/** Draw a rounded rectangle path */
function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

/** Draw a pill-shaped label (e.g. "LDF") */
function drawPill(
  ctx: CanvasRenderingContext2D,
  text: string,
  bg: string,
  x: number, y: number,
  fontSize: number,
  padX = 24, padY = 12
) {
  ctx.font = `700 ${fontSize}px 'DM Sans', system-ui, sans-serif`;
  const tw = ctx.measureText(text).width;
  const pw = tw + padX * 2;
  const ph = fontSize + padY * 2;
  roundRect(ctx, x, y, pw, ph, ph / 2);
  ctx.fillStyle = bg;
  ctx.fill();
  ctx.fillStyle = '#FFFFFF';
  ctx.fillText(text, x + padX, y + ph - padY - 2);
  return { w: pw, h: ph };
}

// ─────────────────────────────────────────────────────────────────────────────
// Main draw function
// ─────────────────────────────────────────────────────────────────────────────
function drawCard(
  ctx: CanvasRenderingContext2D,
  W: number, H: number,
  data: ShareCardData
) {
  const al = data.leaderAlliance || 'OTH';
  const is916 = H === 1920;
  const scale = is916 ? 1 : 0.78; // 4:5 proportional scale

  // ── 1. Background gradient ───────────────────────────────────────────────
  const [c1, c2] = BG_GRADIENTS[al] ?? BG_GRADIENTS.OTH;
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, c1);
  grad.addColorStop(1, c2);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  // Subtle diagonal texture lines
  ctx.save();
  ctx.globalAlpha = 0.04;
  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 1;
  for (let i = -H; i < W + H; i += 80) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i + H, H);
    ctx.stroke();
  }
  ctx.restore();

  // ── 2. Accent bar at top ─────────────────────────────────────────────────
  ctx.fillStyle = accent(al);
  ctx.fillRect(0, 0, W, 8);

  const PAD = 72; // horizontal padding
  let curY = 72;

  // ── 3. TOP ZONE — Branding ───────────────────────────────────────────────
  const brandSize = Math.round(28 * scale);
  ctx.font = `700 ${brandSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.fillText('KERALA ELECTIONS', PAD, curY + brandSize);

  const yearSize = Math.round(28 * scale);
  const yearText = '2026';
  ctx.font = `800 ${yearSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = accent(al);
  const yearX = W - PAD - ctx.measureText(yearText).width;
  ctx.fillText(yearText, yearX, curY + yearSize);

  curY += Math.round(60 * scale);

  // Thin separator
  ctx.fillStyle = 'rgba(255,255,255,0.12)';
  ctx.fillRect(PAD, curY, W - PAD * 2, 1);
  curY += Math.round(52 * scale);

  // ── 4. CONSTITUENCY ZONE ─────────────────────────────────────────────────
  const numSize = Math.round(22 * scale);
  ctx.font = `600 ${numSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.45)';
  ctx.fillText(`#${String(data.constituencyNumber).padStart(3, '0')} · ${data.district.toUpperCase()} DISTRICT`, PAD, curY + numSize);
  curY += Math.round(52 * scale);

  const nameSize = Math.round(88 * scale);
  ctx.font = `800 ${nameSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = '#FFFFFF';
  const fittedName = fitText(ctx, data.constituencyName.toUpperCase(), W - PAD * 2);
  ctx.fillText(fittedName, PAD, curY + nameSize);
  curY += Math.round(nameSize + 36 * scale);

  // ── 5. STATUS BADGE ──────────────────────────────────────────────────────
  const isDeclared = data.status === 'RESULT_DECLARED';
  const statusText = isDeclared
    ? '✓  RESULT DECLARED'
    : data.status === 'IN_PROGRESS'
      ? `▲  COUNTING IN PROGRESS · ${data.countingPct}% COUNTED`
      : '○  COUNTING NOT STARTED';
  const statusSize = Math.round(22 * scale);
  const statusBg = isDeclared ? 'rgba(34,197,94,0.18)' : 'rgba(255,255,255,0.08)';
  const statusFg = isDeclared ? '#4ADE80' : 'rgba(255,255,255,0.6)';

  ctx.font = `700 ${statusSize}px 'DM Sans', system-ui, sans-serif`;
  const statusW = ctx.measureText(statusText).width + 48;
  const statusH = statusSize + 28;
  roundRect(ctx, PAD, curY, statusW, statusH, 10);
  ctx.fillStyle = statusBg;
  ctx.fill();
  ctx.fillStyle = statusFg;
  ctx.fillText(statusText, PAD + 24, curY + statusH - 14);
  curY += Math.round(statusH + 60 * scale);

  // ── 6. WINNER / LEADING BLOCK ────────────────────────────────────────────
  // Glass card background
  roundRect(ctx, PAD, curY, W - PAD * 2, Math.round(340 * scale), 24);
  ctx.fillStyle = 'rgba(255,255,255,0.07)';
  ctx.fill();
  roundRect(ctx, PAD, curY, W - PAD * 2, Math.round(340 * scale), 24);
  ctx.strokeStyle = 'rgba(255,255,255,0.15)';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  const innerX = PAD + 40;
  let blockY = curY + Math.round(38 * scale);

  // "Winner" / "Leading" label
  const roleSize = Math.round(20 * scale);
  ctx.font = `700 ${roleSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = accent(al);
  ctx.letterSpacing = '3px';
  ctx.fillText(isDeclared ? '✓  WINNER' : '▲  LEADING', innerX, blockY + roleSize);
  ctx.letterSpacing = '0px';
  blockY += Math.round(roleSize + 20 * scale);

  // Candidate name
  const candSize = Math.round(64 * scale);
  ctx.font = `800 ${candSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = '#FFFFFF';
  const fittedCand = fitText(ctx, data.leaderName, W - PAD * 2 - 80);
  ctx.fillText(fittedCand, innerX, blockY + candSize);
  blockY += Math.round(candSize + 16 * scale);

  // Party + Alliance pill row
  const partySize = Math.round(24 * scale);
  ctx.font = `500 ${partySize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.65)';
  ctx.fillText(data.leaderParty, innerX, blockY + partySize);
  const partyW = ctx.measureText(data.leaderParty).width;

  const pillOut = drawPill(
    ctx, al, labelBg(al),
    innerX + partyW + 20, blockY - 4,
    Math.round(20 * scale), 16, 10
  );
  blockY += Math.round(partySize + 20 * scale);

  // Votes & Percentage row
  const voteSize = Math.round(44 * scale);
  ctx.font = `800 ${voteSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = accent(al);
  ctx.fillText(data.leaderVotes.toLocaleString('en-IN'), innerX, blockY + voteSize);
  const votesW = ctx.measureText(data.leaderVotes.toLocaleString('en-IN')).width;

  const pctSize = Math.round(24 * scale);
  ctx.font = `600 ${pctSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.5)';
  ctx.fillText(`${data.leaderPct.toFixed(1)}%`, innerX + votesW + 20, blockY + voteSize - 6);

  curY += Math.round(340 * scale) + Math.round(40 * scale);

  // ── 7. MARGIN BLOCK ──────────────────────────────────────────────────────
  if (data.margin !== null && data.margin > 0) {
    const marginSize = Math.round(80 * scale);
    ctx.font = `800 ${marginSize}px 'DM Sans', system-ui, sans-serif`;
    ctx.fillStyle = accent(al);
    const marginStr = '+' + data.margin.toLocaleString('en-IN');
    ctx.fillText(marginStr, PAD, curY + marginSize);

    const mLabelSize = Math.round(22 * scale);
    ctx.font = `500 ${mLabelSize}px 'DM Sans', system-ui, sans-serif`;
    ctx.fillStyle = 'rgba(255,255,255,0.45)';
    ctx.fillText('margin over 2nd place', PAD, curY + marginSize + Math.round(32 * scale));
    curY += Math.round(marginSize + 80 * scale);
  } else {
    curY += Math.round(30 * scale);
  }

  // ── 8. RUNNER-UP + OTHER CANDIDATES BLOCK ────────────────────────────────
  // Build the full "others" list: runner-up first, then otherCandidates (3rd/4th)
  type OtherRow = { rank: number; name: string; party: string; alliance: string; votes: number; pct: number };
  const otherRows: OtherRow[] = [];
  if (data.runnerUpName) {
    otherRows.push({
      rank: 2,
      name: data.runnerUpName,
      party: data.runnerUpParty ?? '',
      alliance: data.runnerUpAlliance ?? 'OTH',
      votes: data.runnerUpVotes,
      pct: data.runnerUpPct,
    });
  }
  data.otherCandidates.forEach((c, i) => otherRows.push({ rank: i + 3, ...c }));

  if (otherRows.length > 0) {
    // Separator
    ctx.fillStyle = 'rgba(255,255,255,0.10)';
    ctx.fillRect(PAD, curY, W - PAD * 2, 1);
    curY += Math.round(32 * scale);

    // Section label
    const othLabelSize = Math.round(18 * scale);
    ctx.font = `600 ${othLabelSize}px 'DM Sans', system-ui, sans-serif`;
    ctx.fillStyle = 'rgba(255,255,255,0.30)';
    ctx.fillText('OTHER CANDIDATES', PAD, curY + othLabelSize);
    curY += Math.round(othLabelSize + 20 * scale);

    // Max pct for bar scaling — leader is always the max
    const maxPct = data.leaderPct;

    for (const row of otherRows) {
      const rowH = Math.round(74 * scale);
      const rowW = W - PAD * 2;

      // Row background — subtle glass
      roundRect(ctx, PAD, curY, rowW, rowH, 10);
      ctx.fillStyle = 'rgba(255,255,255,0.04)';
      ctx.fill();

      // Rank number
      const rankSize = Math.round(18 * scale);
      ctx.font = `700 ${rankSize}px 'DM Sans', system-ui, sans-serif`;
      ctx.fillStyle = 'rgba(255,255,255,0.25)';
      ctx.fillText(`${row.rank}`, PAD + 16, curY + Math.round(26 * scale));

      // Name
      const nSize = Math.round(26 * scale);
      ctx.font = `700 ${nSize}px 'DM Sans', system-ui, sans-serif`;
      ctx.fillStyle = row.rank === 2 ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.72)';
      const maxNameW = rowW - Math.round(240 * scale);
      const fittedN = fitText(ctx, row.name, maxNameW);
      ctx.fillText(fittedN, PAD + Math.round(44 * scale), curY + Math.round(28 * scale));

      // Party · Alliance tag
      const pTagSize = Math.round(18 * scale);
      ctx.font = `500 ${pTagSize}px 'DM Sans', system-ui, sans-serif`;
      ctx.fillStyle = 'rgba(255,255,255,0.38)';
      const partyTag = row.party + (row.alliance && row.alliance !== 'OTH' ? ' · ' + row.alliance : '');
      ctx.fillText(partyTag, PAD + Math.round(44 * scale), curY + Math.round(28 * scale) + Math.round(pTagSize + 6 * scale));

      // Pct on the right (all rows)
      if (row.pct > 0) {
        const pctNumSize = Math.round(26 * scale);
        ctx.font = `700 ${pctNumSize}px 'DM Sans', system-ui, sans-serif`;
        ctx.fillStyle = 'rgba(255,255,255,0.65)';
        const pctStr = row.pct.toFixed(1) + '%';
        const pctStrW = ctx.measureText(pctStr).width;
        ctx.fillText(pctStr, PAD + rowW - pctStrW - 16, curY + Math.round(28 * scale));

        // Mini bar at bottom of row
        const miniBarY = curY + rowH - Math.round(10 * scale);
        const miniBarW = rowW - 32;
        // track
        roundRect(ctx, PAD + 16, miniBarY, miniBarW, Math.round(5 * scale), Math.round(2.5 * scale));
        ctx.fillStyle = 'rgba(255,255,255,0.08)';
        ctx.fill();
        // fill — alliance colour at reduced opacity
        roundRect(ctx, PAD + 16, miniBarY, miniBarW * Math.min(1, row.pct / (maxPct || 1)), Math.round(5 * scale), Math.round(2.5 * scale));
        ctx.fillStyle = ALLIANCE_ACCENT[row.alliance] ?? 'rgba(255,255,255,0.3)';
        ctx.globalAlpha = 0.6;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      curY += rowH + Math.round(8 * scale);
    }

    curY += Math.round(16 * scale);
  }

  // ── 9. FLIP BADGE ────────────────────────────────────────────────────────
  if (data.isFlip && data.sittingAlliance) {
    curY += Math.round(16 * scale);
    const flipText = `🔄  Seat flipped: ${data.sittingAlliance} → ${data.leaderAlliance}`;
    const flipSize = Math.round(22 * scale);
    ctx.font = `700 ${flipSize}px 'DM Sans', system-ui, sans-serif`;
    const flipW = ctx.measureText(flipText).width + 40;
    const flipH = flipSize + 24;
    roundRect(ctx, PAD, curY, flipW, flipH, 10);
    ctx.fillStyle = 'rgba(255,200,100,0.15)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,200,100,0.5)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = '#FCD34D';
    ctx.fillText(flipText, PAD + 20, curY + flipH - 12);
    curY += Math.round(flipH + 24 * scale);
  }

  // ── 10. BOTTOM ZONE ──────────────────────────────────────────────────────
  const bottomH = Math.round(180 * scale);
  const bottomY = H - bottomH - 8; // 8px from accent bar at bottom

  // Bottom accent bar
  ctx.fillStyle = accent(al);
  ctx.fillRect(0, H - 8, W, 8);

  // Separator
  ctx.fillStyle = 'rgba(255,255,255,0.10)';
  ctx.fillRect(PAD, bottomY, W - PAD * 2, 1);

  // Alliance seat bar (visual representation)
  const barY = bottomY + Math.round(24 * scale);
  const barW = W - PAD * 2;
  const barH = Math.round(8 * scale);

  // Background track
  roundRect(ctx, PAD, barY, barW, barH, barH / 2);
  ctx.fillStyle = 'rgba(255,255,255,0.1)';
  ctx.fill();
  // Alliance fill
  roundRect(ctx, PAD, barY, barW * (data.leaderPct / 100), barH, barH / 2);
  ctx.fillStyle = accent(al);
  ctx.fill();

  // URL / site branding
  const urlSize = Math.round(24 * scale);
  ctx.font = `600 ${urlSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.5)';
  const urlText = 'kl-2026.firebaseapp.com';
  const signoffY = barY + barH + Math.round(44 * scale);
  ctx.fillText(urlText, PAD, signoffY);

  // Reddit handle
  const redditSize = Math.round(20 * scale);
  ctx.font = `500 ${redditSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.fillText('u/dasharath_writes', PAD, signoffY + Math.round(redditSize + 10 * scale));

  // Timestamp
  const tsSize = Math.round(16 * scale);
  ctx.font = `400 ${tsSize}px 'DM Sans', system-ui, sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.22)';
  const now = new Date();
  const ts = now.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }) + ' IST';
  ctx.fillText(ts, PAD, signoffY + Math.round(redditSize + 10 * scale) + Math.round(tsSize + 10 * scale));
}

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Generate a share card PNG as a Blob.
 * Waits for document.fonts.ready so web fonts (DM Sans) render correctly.
 */
export async function generateShareCard(
  data: ShareCardData,
  format: ShareFormat
): Promise<Blob> {
  const { w, h } = FORMATS[format];

  // Wait for fonts so DM Sans renders in canvas
  await document.fonts.ready;

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  drawCard(ctx, w, h, data);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Canvas toBlob returned null'));
      },
      'image/png',
      1.0
    );
  });
}

/**
 * Trigger a file download for a given Blob.
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
