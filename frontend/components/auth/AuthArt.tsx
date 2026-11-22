/**
 * @file components/auth/AuthArt.tsx
 * @brief Decorative Aegean mosaic for the auth split card: twelve tiles of
 *        island motifs (domes, sun, Greek key, waves, olive, arches, sea).
 *        Colours come from the theme tokens (plus color-mix tints), so the
 *        art follows dark mode and admin branding. aria-hidden.
 */

const mix = (a: string, pct: number, b = "var(--color-bg)") =>
  `color-mix(in oklab, var(--color-${a}) ${pct}%, ${b})`;

/** @brief Tile colours, all derived from theme tokens. */
const C = {
  navy: "var(--color-ink)",
  sea: "var(--color-accent)",
  wave: mix("accent", 70, "white"),
  sky: "var(--color-blue)",
  sand: mix("sun", 28),
  cream: "var(--color-bg)",
  sun: "var(--color-sun)",
  clay: "var(--color-red)",
  rose: mix("red", 45),
  olive: "var(--color-leaf)",
  leaf: mix("leaf", 60),
};

/** @brief Greek key (meander) band, one unit per 40px. */
function Meander({ x, y, n }: { x: number; y: number; n: number }) {
  const d = Array.from({ length: n }, (_, i) => {
    const o = x + i * 40;
    return `M${o} ${y + 30}V${y}H${o + 30}V${y + 22}H${o + 10}V${y + 10}H${o + 20}`;
  }).join("");
  return <path d={d} fill="none" style={{ stroke: C.cream }} strokeWidth={4} />;
}

/** @brief Mosaic illustration (fills its box, cropping as needed). */
export function AuthArt() {
  return (
    <svg
      viewBox="0 0 600 800"
      preserveAspectRatio="xMidYMid slice"
      className="block size-full"
      aria-hidden
      focusable="false"
    >
      {/* Row 1: dome, sun, Greek key */}
      <rect width="200" height="200" style={{ fill: C.sky }} />
      <path d="M40 200V110a60 60 0 0 1 120 0v90z" style={{ fill: C.cream }} />
      <path d="M60 110a40 40 0 0 1 80 0z" style={{ fill: C.sea }} />
      <rect x="96" y="56" width="8" height="18" style={{ fill: C.sea }} />
      <rect
        x="85"
        y="140"
        width="30"
        height="60"
        rx="15"
        style={{ fill: C.wave }}
      />

      <rect x="200" width="200" height="200" style={{ fill: C.sand }} />
      <g style={{ fill: C.sun }}>
        <circle cx="300" cy="100" r="38" />
        {Array.from({ length: 12 }, (_, i) => (
          <rect
            key={i}
            x="297"
            y="30"
            width="6"
            height="20"
            rx="3"
            transform={`rotate(${i * 30} 300 100)`}
          />
        ))}
      </g>

      <rect x="400" width="200" height="200" style={{ fill: C.sea }} />
      <Meander x={420} y={40} n={4} />
      <Meander x={420} y={130} n={4} />
      <rect x="420" y="90" width="150" height="4" style={{ fill: C.sky }} />

      {/* Row 2: waves spanning two tiles, olive sprig */}
      <rect y="200" width="400" height="200" style={{ fill: C.wave }} />
      {[250, 290, 330, 370].map((y, i) => (
        <path
          key={y}
          d={`M0 ${y}${` q20 ${i % 2 ? 14 : -14} 40 0`.repeat(10)}`}
          fill="none"
          style={{ stroke: i % 2 ? C.sky : C.cream }}
          strokeWidth={4}
          strokeLinecap="round"
          transform={`translate(${i % 2 ? 0 : 20} 0)`}
        />
      ))}

      <rect
        x="400"
        y="200"
        width="200"
        height="200"
        style={{ fill: C.cream }}
      />
      <path
        d="M440 380 Q500 300 560 220"
        fill="none"
        style={{ stroke: C.olive }}
        strokeWidth={4}
      />
      {[0, 1, 2, 3].map((i) => {
        const x = 455 + i * 26;
        const y = 355 - i * 36;
        return (
          <g key={i}>
            <ellipse
              cx={x - 14}
              cy={y - 6}
              rx="18"
              ry="7"
              style={{ fill: C.olive }}
              transform={`rotate(-35 ${x - 14} ${y - 6})`}
            />
            <ellipse
              cx={x + 12}
              cy={y + 8}
              rx="18"
              ry="7"
              style={{ fill: C.leaf }}
              transform={`rotate(-55 ${x + 12} ${y + 8})`}
            />
          </g>
        );
      })}
      <circle cx="520" cy="300" r="8" style={{ fill: C.navy }} />

      {/* Row 3: doorway arches, terracotta quarter circles, sunset over sea */}
      <rect y="400" width="200" height="200" style={{ fill: C.clay }} />
      <path d="M50 600V480a50 50 0 0 1 100 0v120z" style={{ fill: C.cream }} />
      <path d="M70 600V490a30 30 0 0 1 60 0v110z" style={{ fill: C.sea }} />

      <rect x="200" y="400" width="200" height="200" style={{ fill: C.rose }} />
      <path d="M200 400h100a100 100 0 0 1-100 100z" style={{ fill: C.clay }} />
      <path d="M400 600H300a100 100 0 0 1 100-100z" style={{ fill: C.cream }} />
      <circle cx="300" cy="500" r="10" style={{ fill: C.navy }} />

      <rect x="400" y="400" width="200" height="400" style={{ fill: C.navy }} />
      <circle cx="500" cy="560" r="70" style={{ fill: C.sun }} />
      <rect x="400" y="560" width="200" height="240" style={{ fill: C.sea }} />
      {[590, 625, 660].map((y) => (
        <rect
          key={y}
          x={430 + (y % 3) * 4}
          y={y}
          width="140"
          height="5"
          rx="2.5"
          style={{ fill: C.sky }}
          opacity="0.7"
        />
      ))}

      {/* Row 4: dots, olive field */}
      <rect y="600" width="200" height="200" style={{ fill: C.sand }} />
      {Array.from({ length: 25 }, (_, i) => (
        <circle
          key={i}
          cx={40 + (i % 5) * 30}
          cy={640 + Math.floor(i / 5) * 30}
          r="5"
          style={{ fill: C.sea }}
        />
      ))}

      <rect
        x="200"
        y="600"
        width="200"
        height="200"
        style={{ fill: C.olive }}
      />
      <path d="M200 800a100 100 0 0 1 200 0z" style={{ fill: C.leaf }} />
      <path d="M240 800a60 60 0 0 1 120 0z" style={{ fill: C.cream }} />
      <rect x="296" y="630" width="8" height="60" style={{ fill: C.cream }} />
    </svg>
  );
}
