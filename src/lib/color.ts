const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

export const hsvToRgb = (
  h: number,
  s: number,
  v: number,
): [number, number, number] => {
  const hNorm = ((h % 360) + 360) % 360;
  const sNorm = clamp(s, 0, 100) / 100;
  const vNorm = clamp(v, 0, 100) / 100;

  if (sNorm === 0) {
    const gray = Math.round(vNorm * 255);
    return [gray, gray, gray];
  }

  const sectorFloat = hNorm / 60;
  const sector = Math.floor(sectorFloat);
  const f = sectorFloat - sector;

  const p = vNorm * (1 - sNorm);
  const q = vNorm * (1 - sNorm * f);
  const t = vNorm * (1 - sNorm * (1 - f));

  let r = vNorm;
  let g = vNorm;
  let b = vNorm;

  switch (sector) {
    case 0:
      r = vNorm;
      g = t;
      b = p;
      break;
    case 1:
      r = q;
      g = vNorm;
      b = p;
      break;
    case 2:
      r = p;
      g = vNorm;
      b = t;
      break;
    case 3:
      r = p;
      g = q;
      b = vNorm;
      break;
    case 4:
      r = t;
      g = p;
      b = vNorm;
      break;
    default:
      r = vNorm;
      g = p;
      b = q;
      break;
  }

  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
};

export const hsvToHex = (h: number, s: number, v: number): string => {
  const [r, g, b] = hsvToRgb(h, s, v);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`.toUpperCase();
};

export const hexToHsv = (hex: string): [number, number, number] => {
  const normalized = hex.replace("#", "");
  const r = parseInt(normalized.slice(0, 2), 16) / 255;
  const g = parseInt(normalized.slice(2, 4), 16) / 255;
  const b = parseInt(normalized.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;

  const value = max * 100;
  const saturation = max === 0 ? 0 : (delta / max) * 100;

  let hue = 0;
  if (delta !== 0) {
    if (max === r) {
      hue = ((g - b) / delta + (g < b ? 6 : 0)) * 60;
    } else if (max === g) {
      hue = ((b - r) / delta + 2) * 60;
    } else {
      hue = ((r - g) / delta + 4) * 60;
    }
  }

  return [Math.round(hue), Math.round(saturation), Math.round(value)];
};
