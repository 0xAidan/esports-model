"""Tiny accessible operator table. Tailwind classes only."""

from __future__ import annotations

from html import escape
from typing import Any, assert_never

from esports_model.ev.gates import Action


def render_operator_html(snapshot: dict[str, Any], *, refresh_sec: int) -> str:
    diagnostic = str(snapshot.get("diagnostic") or "pipeline_error")
    detail = str(snapshot.get("diagnostic_detail") or "")
    generated = str(snapshot.get("generated_at") or "")
    counts = snapshot.get("counts") or {}
    rows = snapshot.get("rows") or []
    banner = _banner_class(diagnostic)
    body_rows = "".join(_row_html(row) if isinstance(row, dict) else "" for row in rows)
    if not body_rows:
        body_rows = (
            '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-400">'
            "No series books in the snapshot yet."
            "</td></tr>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>esports-model scanner</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100">
  <main class="mx-auto max-w-6xl px-4 py-6">
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">CS2 +EV scanner</h1>
        <p class="text-sm text-slate-400">Signal only. No orders are placed.</p>
      </div>
      <button
        type="button"
        id="refresh-button"
        class="rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-300"
        tabindex="0"
        aria-label="Refresh markets and snapshot"
        onclick="handleRefresh()"
        onkeydown="handleRefreshKey(event)"
      >
        Refresh markets
      </button>
    </div>
    <p
      id="diagnostic"
      class="mb-4 rounded-md px-3 py-2 text-sm {banner}"
      role="status"
      aria-live="polite"
    >
      <span class="font-semibold">{escape(diagnostic)}</span>
      — {escape(detail)}
      <span class="block text-xs opacity-80">Updated {escape(generated)}</span>
    </p>
    <p class="mb-3 text-sm text-slate-300">
      BET {int(counts.get("BET", 0))}
      · WATCH {int(counts.get("WATCH", 0))}
      · PASS {int(counts.get("PASS", 0))}
      · quarantine {int(counts.get("quarantine", 0))}
    </p>
    <div class="overflow-x-auto rounded-lg border border-slate-800">
      <table class="min-w-full text-left text-sm">
        <caption class="sr-only">
          Model probability versus Polymarket ask, net EV, and action
        </caption>
        <thead class="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th scope="col" class="px-3 py-2">Side</th>
            <th scope="col" class="px-3 py-2">Vs</th>
            <th scope="col" class="px-3 py-2">Model p</th>
            <th scope="col" class="px-3 py-2">Ask</th>
            <th scope="col" class="px-3 py-2">Net EV</th>
            <th scope="col" class="px-3 py-2">Volume</th>
            <th scope="col" class="px-3 py-2">Spread</th>
            <th scope="col" class="px-3 py-2">Depth</th>
            <th scope="col" class="px-3 py-2">Action</th>
            <th scope="col" class="px-3 py-2">Stake</th>
          </tr>
        </thead>
        <tbody id="scan-body" class="divide-y divide-slate-800">{body_rows}</tbody>
      </table>
    </div>
  </main>
  <script>
    const REFRESH_SEC = {int(refresh_sec)};
    const handleRefresh = async () => {{
      const button = document.getElementById("refresh-button");
      if (button) button.setAttribute("aria-busy", "true");
      try {{
        await fetch("/refresh", {{ method: "POST" }});
        window.location.reload();
      }} catch (error) {{
        window.location.reload();
      }}
    }};
    const handleRefreshKey = (event) => {{
      if (event.key === "Enter" || event.key === " ") {{
        event.preventDefault();
        handleRefresh();
      }}
    }};
    window.setInterval(() => {{
      fetch("/snapshot.json")
        .then((response) => response.json())
        .then((payload) => {{
          const node = document.getElementById("diagnostic");
          if (node && payload.diagnostic) {{
            node.innerHTML =
              "<span class=\\"font-semibold\\">" + payload.diagnostic + "</span> — " +
              (payload.diagnostic_detail || "") +
              "<span class=\\"block text-xs opacity-80\\">Updated " +
              (payload.generated_at || "") + "</span>";
          }}
        }})
        .catch(() => {{}});
    }}, REFRESH_SEC * 1000);
  </script>
</body>
</html>
"""


def _banner_class(diagnostic: str) -> str:
    if diagnostic == "edges_available":
        return "bg-emerald-950 text-emerald-100 border border-emerald-700"
    if diagnostic == "market_available_no_edges":
        return "bg-slate-900 text-slate-200 border border-slate-700"
    if diagnostic == "no_market_posted_yet":
        return "bg-amber-950 text-amber-100 border border-amber-700"
    return "bg-rose-950 text-rose-100 border border-rose-700"


def _as_action(value: object) -> Action:
    if value in {"BET", "WATCH", "PASS", "quarantine"}:
        return value  # type: ignore[return-value]
    return "WATCH"


def _row_html(row: dict[str, Any]) -> str:
    action = _as_action(row.get("action"))
    return (
        f"<tr class='{ _row_class(action) }'>"
        f"<td class='px-3 py-2 font-medium'>{escape(str(row.get('side') or '-'))}</td>"
        f"<td class='px-3 py-2'>{escape(str(row.get('opponent') or '-'))}</td>"
        f"<td class='px-3 py-2'>{_fmt(row.get('model_p'))}</td>"
        f"<td class='px-3 py-2'>{_fmt(row.get('ask'))}</td>"
        f"<td class='px-3 py-2'>{_fmt(row.get('ev_net'), signed=True)}</td>"
        f"<td class='px-3 py-2'>{_fmt_money(row.get('volume'))}</td>"
        f"<td class='px-3 py-2'>{_fmt(row.get('spread'))}</td>"
        f"<td class='px-3 py-2'>{_fmt_money(row.get('depth_usd'))}</td>"
        f"<td class='px-3 py-2 font-semibold'>{escape(str(action))}</td>"
        f"<td class='px-3 py-2'>{_fmt_money(row.get('stake_usd'))}</td>"
        "</tr>"
    )


def _row_class(action: Action) -> str:
    if action == "BET":
        return "bg-emerald-950/40"
    if action == "WATCH":
        return "bg-amber-950/20"
    if action == "PASS":
        return ""
    if action == "quarantine":
        return "bg-rose-950/30"
    assert_never(action)


def _fmt(value: object, *, signed: bool = False) -> str:
    if value is None:
        return "—"
    number = float(value)
    if signed:
        return f"{number:+.3f}"
    return f"{number:.3f}"


def _fmt_money(value: object) -> str:
    if value is None:
        return "—"
    return f"{float(value):.0f}"
