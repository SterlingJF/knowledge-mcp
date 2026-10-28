# MCP App storyboard

The design source for the knowledge-mcp MCP App: the tokens and the generators that draw every frame on the Doop canvas `MVdPWv1RzA` (knowledge-mcp · MCP App · Storyboard).

`kmtokens.js` is the only place a colour, size, radius, space or motion value is set. Token names are the MCP Apps host style variables, and the values are Claude's documented values, used as fallbacks outside a host. Change a value here and re-render; never edit a frame on the canvas by hand.

| File            | Draws                                                                              |
| --------------- | ---------------------------------------------------------------------------------- |
| `kmtokens.js`   | Tokens, roles, type scale, radius, space, motion and touch target                  |
| `kmgen.js`      | Shared CSS and parts: card, badge, button, chips, full-view frame                  |
| `ds.js`         | 00 Foundations, 00 Components and 00 Patterns sheets, F00 requirements included    |
| `overview.js`   | 00 Overview                                                                        |
| `flow03.js`     | 03 Evidence review                                                                 |
| `flows_rest.js` | 01, 02 and 04 to 08                                                                |
| `surfaces.js`   | Each flow's "Every surface" frame: app, text cards, MCP, CLI and API               |
| `text_cards.js` | Text cards and CLI output captured from knowledge-mcp 0.4.0 on the storyboard data |

## Render

Load the files in a page on the Doop server, in this order: `kmtokens.js`, `kmgen.js`, `text_cards.js`, `flow03.js`, `flows_rest.js`, `overview.js`, `ds.js`, `surfaces.js`. Then `KM.frame(theme, spec)`, `DS.html(theme, sheet)`, `SURF.html(theme, pageId)` and `OVERVIEW(theme)` return each frame's HTML; `theme` is `''` or `'dark'`.

An inline card with more than five data points throws: Claude's limit for inline cards.
