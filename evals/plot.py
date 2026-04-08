"""
Generate an intuitive bar chart comparing skill output length vs the
terse control arm — side by side, so the visual gap IS the gain.

Reads evals/snapshots/results.json and writes:
  - evals/snapshots/results.html  (interactive plotly)
  - evals/snapshots/results.png   (static export for README/PR embed)

Run: uv run --with tiktoken --with plotly --with kaleido python evals/plot.py
"""

from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
import tiktoken

ENCODING = tiktoken.get_encoding("o200k_base")
SNAPSHOT = Path(__file__).parent / "snapshots" / "results.json"
HTML_OUT = Path(__file__).parent / "snapshots" / "results.html"
PNG_OUT = Path(__file__).parent / "snapshots" / "results.png"


def count(text: str) -> int:
    return len(ENCODING.encode(text))


def main() -> None:
    data = json.loads(SNAPSHOT.read_text())
    arms = data["arms"]
    meta = data.get("metadata", {})

    terse_total = sum(count(o) for o in arms["__terse__"])

    rows = []
    for skill, outputs in arms.items():
        if skill in ("__baseline__", "__terse__"):
            continue
        skill_total = sum(count(o) for o in outputs)
        saved = terse_total - skill_total
        pct = (saved / terse_total) * 100 if terse_total else 0.0
        rows.append(
            {"skill": skill, "skill_total": skill_total, "saved": saved, "pct": pct}
        )

    rows.sort(
        key=lambda r: r["pct"]
    )  # ascending → biggest gain at top in horizontal bar
    names = [r["skill"] for r in rows]
    skill_totals = [r["skill_total"] for r in rows]
    saved = [r["saved"] for r in rows]
    pcts = [r["pct"] for r in rows]

    fig = go.Figure()

    # the part the skill still uses (what you pay)
    fig.add_trace(
        go.Bar(
            y=names,
            x=skill_totals,
            orientation="h",
            name="tokens used",
            marker=dict(color="#4c78a8"),
            text=[f"{t}" for t in skill_totals],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=13),
            hovertemplate="<b>%{y}</b><br>tokens used: %{x}<extra></extra>",
        )
    )

    # the part the skill saved (the win), stacked on top
    fig.add_trace(
        go.Bar(
            y=names,
            x=saved,
            orientation="h",
            name="tokens saved",
            marker=dict(color="#2ca02c"),
            text=[f"−{s}  ({p:.0f}% less)" for s, p in zip(saved, pcts)],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=13),
            hovertemplate="<b>%{y}</b><br>tokens saved: %{x} (%{customdata:.0f}%)<extra></extra>",
            customdata=pcts,
        )
    )

    # reference line: where the terse control sits (= 100% of what you'd pay without the skill)
    fig.add_vline(
        x=terse_total,
        line=dict(color="black", width=2, dash="dash"),
        annotation_text=f"  no skill = {terse_total} tokens",
        annotation_position="top right",
        annotation_font=dict(size=11, color="black"),
    )

    fig.update_layout(
        title=dict(
            text=f"<b>How much shorter does each skill make Claude's answers?</b><br>"
            f"<sub>{meta.get('model', '?')} · {meta.get('n_prompts', '?')} prompts · "
            f"compared against a plain <i>'Answer concisely.'</i> baseline</sub>",
            x=0.5,
            xanchor="center",
        ),
        barmode="stack",
        xaxis=dict(
            title="Total output tokens across all prompts",
            zeroline=False,
            gridcolor="rgba(0,0,0,0.08)",
            range=[0, terse_total * 1.15],
        ),
        yaxis=dict(title=""),
        plot_bgcolor="white",
        height=420,
        width=950,
        margin=dict(l=120, r=80, t=100, b=70),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5
        ),
    )

    fig.write_html(HTML_OUT)
    print(f"Wrote {HTML_OUT}")
    fig.write_image(PNG_OUT, scale=2)
    print(f"Wrote {PNG_OUT}")


if __name__ == "__main__":
    main()
