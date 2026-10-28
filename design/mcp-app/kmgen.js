// knowledge-mcp MCP App storyboard generator: one design system, light and dark from the same specs.
window.KM = (() => {
  // All values come from window.KMT (kmtokens.js); a component names a token, never a raw value.
  const T = window.KMT;
  const decl = (o) =>
    Object.entries(o)
      .map(([k, v]) => `${k}:${v}`)
      .join(";");
  const css = `
*{margin:0;box-sizing:border-box}
:root{${decl(T.color.light)};${decl(T.font)};${decl(T.radius)};${decl(T.border)};${decl(T.space)};${decl(T.motion)};${decl(T.touch)};color-scheme:light dark}
.dark{${decl(T.color.dark)};color-scheme:dark}
body{font:var(--font-text-sm-size)/var(--font-text-sm-line-height) var(--font-sans);background:var(--color-background-tertiary);color:var(--color-text-primary);width:960px}
.mono{font-family:var(--font-mono);font-size:var(--font-text-xs-size)}
.stage{padding:28px 100px 18px}
.host{border:1px dashed var(--color-border-secondary);border-radius:var(--border-radius-xl);padding:16px 18px;position:relative}
.host>.tag{position:absolute;top:-9px;left:14px;background:var(--color-background-tertiary);padding:0 6px;font-size:var(--font-text-xs-size);color:var(--color-text-tertiary);letter-spacing:.04em}
.ubox{display:flex;flex-direction:column;align-items:flex-end;gap:var(--km-space-2);margin-bottom:var(--km-space-5)}
.uscope{font-size:var(--font-text-xs-size);color:var(--color-text-tertiary);display:flex;gap:var(--km-space-2);align-items:center}
.ubub{background:var(--color-background-secondary);border-radius:14px;padding:8px 14px;max-width:70%}
.ubub.sent{background:transparent;border:1px dashed var(--color-border-secondary)}
.tl{display:flex;gap:var(--km-space-4);align-items:center;color:var(--color-text-tertiary);font-size:var(--font-text-xs-size);margin:3px 0}
.tl .mono{color:var(--color-text-primary)}
.say{margin:10px 0}
.comp{margin-top:var(--km-space-5);border:1px solid var(--color-border-tertiary);border-radius:12px;padding:9px 10px;display:flex;align-items:center;gap:10px;background:var(--color-background-primary)}
.comp .ph{color:var(--color-text-tertiary);flex:1}
.send{width:26px;height:26px;border-radius:var(--border-radius-md);background:var(--color-background-inverse);color:var(--color-text-inverse);display:grid;place-items:center}
.send.off{opacity:.35}
.chip{display:inline-flex;align-items:center;gap:var(--km-space-2);border:var(--border-width-regular) solid var(--color-border-tertiary);border-radius:var(--border-radius-sm);padding:1px 7px;font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height);background:var(--color-background-primary);white-space:nowrap}
svg{width:13px;height:13px;flex:none}
.note svg{margin-top:2px}
/* The card paints no background (transparent theming); the border and padding stand for the host's bordered frame (prefersBorder: true). */
.km{border:var(--border-width-regular) solid var(--color-border-primary);border-radius:var(--border-radius-xl);background:transparent;padding:var(--km-space-6);margin:10px 0}
.kmh{display:flex;justify-content:space-between;gap:var(--km-space-5);align-items:flex-start}
.eb{font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height);font-weight:var(--font-weight-semibold);letter-spacing:.07em;text-transform:uppercase;color:var(--color-text-tertiary)}
.tt{font-weight:var(--font-weight-semibold);font-size:var(--font-heading-md-size);line-height:var(--font-heading-md-line-height);margin-top:var(--km-space-1)}
.meta{color:var(--color-text-tertiary);font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height);margin-top:var(--km-space-1)}
.badge{display:inline-flex;gap:var(--km-space-2);align-items:center;border-radius:var(--border-radius-full);padding:2px 9px;font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height);font-weight:var(--font-weight-semibold);white-space:nowrap}
.b-amb{background:var(--color-background-warning);color:var(--color-text-warning)}.b-grn{background:var(--color-background-success);color:var(--color-text-success)}.b-red{background:var(--color-background-danger);color:var(--color-text-danger)}.b-blu{background:var(--color-background-info);color:var(--color-text-info)}.b-nt{background:var(--color-background-secondary);color:var(--color-text-tertiary)}
table.rows{width:100%;border-collapse:collapse;margin-top:var(--km-space-5)}
.rows th{font-weight:var(--font-weight-semibold);color:var(--color-text-tertiary);font-size:var(--font-text-xs-size);text-align:left;padding:0 var(--km-space-4) var(--km-space-3) 0;border-bottom:var(--border-width-regular) solid var(--color-border-tertiary)}
.rows td{padding:var(--km-space-4) var(--km-space-4) var(--km-space-4) 0;border-bottom:var(--border-width-regular) solid var(--color-border-tertiary);vertical-align:top}
.rows tr:last-child td{border-bottom:0}
.rows tr.out td:not(:first-child){opacity:.45;text-decoration:line-through;text-decoration-color:var(--color-text-tertiary)}
.k{font-weight:var(--font-weight-semibold)}.mu{color:var(--color-text-tertiary)}
.ev{display:flex;width:fit-content;align-items:center;gap:var(--km-space-2);border:var(--border-width-regular) solid var(--color-border-tertiary);border-radius:var(--border-radius-full);padding:0 8px;font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height);font-weight:var(--font-weight-semibold);margin:0 0 var(--km-space-2);background:var(--color-background-primary);white-space:nowrap}
.srcs .chip{margin:0 var(--km-space-2) var(--km-space-2) 0}
.srcs .mu{margin-right:var(--km-space-2)}
.note{display:flex;gap:var(--km-space-4);align-items:flex-start;background:var(--color-background-secondary);border-radius:var(--border-radius-lg);padding:var(--km-space-4) var(--km-space-5);margin-top:var(--km-space-5);font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height)}
.why{color:var(--color-text-tertiary);font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height);margin-top:var(--km-space-5)}
.acts{display:flex;align-items:center;gap:var(--km-space-4);margin-top:var(--km-space-5)}
.btn{display:inline-flex;align-items:center;gap:var(--km-space-3);border-radius:var(--border-radius-md);padding:6px 12px;font-size:var(--font-text-sm-size);line-height:var(--font-text-sm-line-height);font-weight:var(--font-weight-semibold);border:var(--border-width-regular) solid var(--color-border-tertiary);background:var(--color-background-primary);color:var(--color-text-primary)}
.btn.p{background:var(--color-background-inverse);color:var(--color-text-inverse);border-color:var(--color-background-inverse)}
.btn.g{border-color:transparent;background:transparent}
.btn.dis{opacity:.4}
.btn.focus{box-shadow:0 0 0 2px var(--color-background-primary),0 0 0 4px var(--color-ring-primary)}
.btn.hover{background:var(--color-background-secondary)}.btn.p.hover{opacity:.88;background:var(--color-background-inverse)}
.sp{flex:1}
.ta{border:var(--border-width-regular) solid var(--color-border-secondary);border-radius:var(--border-radius-lg);padding:var(--km-space-4) var(--km-space-5);color:var(--color-text-tertiary);margin-top:var(--km-space-5);min-height:54px;background:var(--color-background-primary);font-size:var(--font-text-sm-size)}
.frozen{color:var(--color-text-tertiary);font-size:var(--font-text-xs-size);margin-top:var(--km-space-5)}
.prog{height:4px;border-radius:var(--border-radius-full);background:var(--color-background-secondary);margin-top:var(--km-space-5);overflow:hidden}.prog>i{display:block;height:100%;background:var(--color-text-info)}
.diff{border:var(--border-width-regular) solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);margin-top:var(--km-space-5);font-size:var(--font-text-xs-size);overflow:hidden}
.diff div{padding:var(--km-space-2) var(--km-space-5)}.dm{background:var(--color-background-danger);color:var(--color-text-danger);text-decoration:line-through}.dp{background:var(--color-background-success);color:var(--color-text-success)}
.grid2{display:grid;grid-template-columns:150px 1fr;gap:var(--km-space-3) var(--km-space-5);margin-top:var(--km-space-5)}
.cap{margin-top:16px;border-top:1px solid var(--color-border-tertiary);padding:10px 100px 22px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px;font-size:var(--font-text-xs-size);line-height:var(--font-text-xs-line-height)}
.cap b{display:block;letter-spacing:.06em;text-transform:uppercase;color:var(--color-text-tertiary);font-weight:var(--font-weight-semibold);margin-bottom:2px}
.fid{position:absolute;top:8px;right:12px;font:600 11px/1 var(--font-mono);color:var(--color-text-tertiary)}
.spin{width:12px;height:12px;border:2px solid var(--color-border-secondary);border-top-color:var(--color-text-info);border-radius:50%;display:inline-block;animation:km-spin .8s linear infinite}
@keyframes km-spin{to{transform:rotate(360deg)}}
.dim{opacity:.55}
.cn{display:inline-flex;gap:var(--km-space-4);align-items:center;font:var(--font-weight-semibold) var(--font-text-xs-size)/var(--font-text-xs-line-height) var(--font-mono);color:var(--color-text-tertiary);white-space:nowrap}.cn .cb{margin-top:0}
.cb{width:15px;height:15px;border-radius:var(--border-radius-xs);display:inline-grid;place-items:center;background:var(--color-background-inverse);color:var(--color-text-inverse);margin-top:2px}.cb svg{width:11px;height:11px}.cb.off{background:transparent;border:1.5px solid var(--color-border-secondary)}
.pulse{width:7px;height:7px;border-radius:50%;background:currentColor;position:relative;flex:none;margin-right:1px}
.pulse::after{content:'';position:absolute;inset:0;border-radius:50%;background:currentColor;animation:km-pulse var(--km-pulse)}
@keyframes km-pulse{0%{transform:scale(1);opacity:.55}80%,100%{transform:scale(2.6);opacity:0}}
.sk{display:block;background:var(--color-background-secondary);border-radius:var(--border-radius-lg);height:12px;margin-top:var(--km-space-4);animation:km-shimmer var(--km-shimmer)}.sk.t{height:16px;width:60%}.sk.s{width:40%}.sk.row{height:28px}
@keyframes km-shimmer{50%{opacity:.55}}
.seg{display:inline-flex;border:var(--border-width-regular) solid var(--color-border-secondary);border-radius:var(--border-radius-sm);overflow:hidden;white-space:nowrap}.seg>span{padding:4px 10px;font-size:var(--font-text-xs-size);font-weight:var(--font-weight-semibold);color:var(--color-text-tertiary)}.seg>span+span{border-left:var(--border-width-regular) solid var(--color-border-secondary)}.seg>span.on{background:var(--color-background-inverse);color:var(--color-text-inverse)}
.disc{color:var(--color-text-primary);text-decoration:underline;text-underline-offset:2px;font-size:var(--font-text-xs-size);display:inline-flex;gap:4px;align-items:center;margin-top:var(--km-space-4)}
@media (pointer:coarse){.btn,.seg>span{min-height:var(--km-target)}.cn{min-height:var(--km-target)}}
@media (prefers-reduced-motion:reduce){.pulse::after,.spin,.sk{animation:none}}
.hr{display:flex;gap:var(--km-space-4);align-items:center;flex:none}
.xbtn{display:inline-flex;align-items:center;gap:var(--km-space-2);font-size:var(--font-text-xs-size);font-weight:var(--font-weight-semibold);color:var(--color-text-primary);border:var(--border-width-regular) solid var(--color-border-secondary);border-radius:var(--border-radius-md);padding:3px 8px;white-space:nowrap}
@media (pointer:coarse){.xbtn{min-height:var(--km-target)}}
.km.flat{border:0;padding:0;margin:0}
.fs{padding:0}.fsbar{display:flex;justify-content:space-between;align-items:center;padding:12px 18px;border-bottom:1px dashed var(--color-border-secondary);font-weight:var(--font-weight-semibold)}.fsx{color:var(--color-text-tertiary)}
.fsapp{padding:22px 40px 8px;max-width:1080px}.fs .comp{margin:12px 18px 16px}
.tabs{display:flex;gap:var(--km-space-5);border-bottom:var(--border-width-regular) solid var(--color-border-tertiary);margin-top:var(--km-space-5)}.tabs span{padding:6px 0;font-weight:var(--font-weight-semibold);color:var(--color-text-tertiary)}.tabs span.on{color:var(--color-text-primary);box-shadow:inset 0 -2px 0 var(--color-text-primary)}
`;
  const ic = {
    folder:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M1.8 4.2c0-.6.5-1 1-1h3.4l1.4 1.5h5.6c.6 0 1 .4 1 1v6.1c0 .6-.4 1-1 1H2.8c-.5 0-1-.4-1-1z"/></svg>',
    file: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M4 1.8h5l3 3v9.4H4z"/><path d="M9 1.8v3h3M6 8h4M6 10.5h4"/></svg>',
    check:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3.5 8.5l3 3 6-7"/></svg>',
    ok: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="6.2"/><path d="M5.3 8.2l1.8 1.8 3.6-3.8"/></svg>',
    conflict:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 5h9l-2.5-2.5M13 11H4l2.5 2.5"/></svg>',
    partly:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2.2 1.8"><circle cx="8" cy="8" r="5.6"/></svg>',
    suggest:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="4" cy="3.5" r="1.5"/><circle cx="12" cy="3.5" r="1.5"/><path d="M4 5v1.5c0 2 4 2 4 4V14M12 5v1.5c0 2-4 2-4 4"/></svg>',
    left: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="6"/><path d="M4 12L12 4"/></svg>',
    info: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="6.2"/><path d="M8 7.2V11M8 5v.2"/></svg>',
    undo: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5.5 3.5L2.5 6.5l3 3"/><path d="M2.8 6.5h6.7a3.8 3.8 0 010 7.6H7"/></svg>',
    note: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M2.5 3h11v8h-6l-3 2.5V11h-2z"/></svg>',
    move: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2.5 8h10M9.5 5l3 3-3 3"/></svg>',
    link: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M6.5 9.5l3-3M7 4.5l1-1a2.6 2.6 0 013.6 3.6l-1 1M9 11.5l-1 1a2.6 2.6 0 01-3.6-3.6l1-1"/></svg>',
    warn: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M8 2.2l6.2 11H1.8z"/><path d="M8 6.5v3.3M8 11.3v.2"/></svg>',
    book: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M2.5 3h4c.8 0 1.5.7 1.5 1.5V13c0-.6-.5-1-1-1h-4.5zM13.5 3h-4c-.8 0-1.5.7-1.5 1.5V13c0-.6.5-1 1-1h4.5z"/></svg>',
    clock:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="8" r="6.2"/><path d="M8 4.5V8l2.3 1.5"/></svg>',
    x: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
    expand:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M9.5 2.5h4v4M6.5 13.5h-4v-4M13.5 2.5L9 7M2.5 13.5L7 9"/></svg>',
    chev: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 3.5L10.5 8 6 12.5"/></svg>',
  };
  const ev = {
    supported: ["ok", "Supported"],
    partly: ["partly", "Partly answered"],
    conflicting: ["conflict", "Conflicting"],
    suggested: ["suggest", "Suggested"],
  };
  const chip = (icon, text, cls = "") =>
    `<span class="chip ${cls}">${ic[icon] || ""}${text}</span>`;
  const src = (t, slide) =>
    chip(slide ? "book" : "file", `<span class="mono">${t}</span>`);
  const evTag = (k) => `<span class="ev">${ic[ev[k][0]]}${ev[k][1]}</span>`;
  // Waiting on the person: amber badge leads with a pulsing dot.
  const badge = (cls, text, icon) =>
    `<span class="badge ${cls}">${cls === "b-amb" ? '<i class="pulse"></i>' : ""}${icon ? ic[icon] : ""}${text}</span>`;
  const btn = (t, cls = "", icon) =>
    `<span class="btn ${cls}">${icon ? ic[icon] : ""}${t}</span>`;
  const user = (text, scope) =>
    `<div class="ubox"><span class="uscope">${ic.folder}in ${scope}</span><div class="ubub">${text}</div></div>`;
  // A button never writes: it sends this message through the host, and the assistant acts on it.
  const sent = (text) =>
    `<div class="ubox"><span class="uscope">${ic.chev}Sent from the card</span><div class="ubub sent">${text}</div></div>`;
  const tool = (name, res, running) =>
    `<div class="tl">${running ? '<span class="spin"></span>' : ic.ok}<span class="mono">${name}</span>${res ? `<span>→ ${res}</span>` : ""}</div>`;
  const comp = (scope, ph, off) =>
    `<div class="comp">${chip("folder", scope)}<span class="ph">${ph}</span><span class="send ${off ? "off" : ""}">↑</span></div>`;
  // o.full: an inline summary that opens the full view (the app's own fullscreen button, as Claude requires).
  // o.flat: the same card inside the full view, where Claude's fullscreen chrome replaces the border.
  const xbtn = `<span class="xbtn">${ic.expand}Full view</span>`;
  const card = (o) =>
    `<div class="km${o.flat ? " flat" : ""}"><div class="kmh"><div><div class="eb">${o.eb}</div><div class="tt">${o.title}</div>${o.meta ? `<div class="meta">${o.meta}</div>` : ""}</div><span class="hr">${o.badge || ""}${o.full ? xbtn : ""}</span></div>${o.body || ""}${o.acts ? `<div class="acts">${o.acts}</div>` : ""}</div>`;
  // At most five data points: Claude's limit for an inline card.
  const sum = (rows) => {
    if (rows.length > 5) throw new Error("inline card over 5 data points");
    return `<div class="grid2">${rows.map(([a, b]) => `<div class="mu">${a}</div><div>${b}</div>`).join("")}</div>`;
  };
  const fullFrame = (theme, s) =>
    `<!doctype html><html><head><meta charset="utf-8"><meta name="color-scheme" content="light dark"><style>${css}body{width:1280px}.stage{padding:28px 60px 18px}.cap{padding:10px 60px 22px}</style></head><body class="${theme}"><div style="position:relative"><span class="fid">${s.id}</span><div class="stage"><div class="host fs"><span class="tag">HOST FULL SCREEN · Claude draws the header bar, its close button and the composer; the app fills the rest</span><div class="fsbar"><span>knowledge-mcp</span><span class="fsx">${ic.x}</span></div><div class="fsapp">${s.content}</div>${s.composer || ""}</div></div><div class="cap"><div><b>User</b>${s.cap[0]}</div><div><b>Sees</b>${s.cap[1]}</div><div><b>System</b>${s.cap[2]}</div><div><b>Evidence</b>${s.cap[3]}</div></div></div></body></html>`;
  const frame = (theme, s) =>
    s.full
      ? fullFrame(theme, s)
      : `<!doctype html><html><head><meta charset="utf-8"><meta name="color-scheme" content="light dark"><style>${css}</style></head><body class="${theme}"><div style="position:relative"><span class="fid">${s.id}</span><div class="stage"><div class="host"><span class="tag">HOST CHAT · Claude (web, desktop, mobile, Cowork) draws everything outside the card, its border included</span>${s.content}</div></div><div class="cap"><div><b>User</b>${s.cap[0]}</div><div><b>Sees</b>${s.cap[1]}</div><div><b>System</b>${s.cap[2]}</div><div><b>Evidence</b>${s.cap[3]}</div></div></div></body></html>`;
  async function post(canvas, page, s, theme, x, y) {
    const r = await fetch(`/api/canvases/${canvas}/frames`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: `${s.id} · ${s.name}${theme === "dark" ? " · dark" : ""}`,
        html: frame(theme, s),
        width: 960,
        height: s.h,
        x,
        y,
        pageId: page,
      }),
    });
    const j = await r.json();
    return j.id;
  }
  return {
    css,
    ic,
    ev,
    chip,
    src,
    evTag,
    badge,
    btn,
    user,
    sent,
    tool,
    sum,
    xbtn,
    comp,
    card,
    frame,
    post,
  };
})();
("loaded");
