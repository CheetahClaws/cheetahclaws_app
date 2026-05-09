# `/brainstorm` — moderated multi-round expert debate

`/brainstorm` runs a structured debate between AI personas about your
topic. It's not a single LLM call dressed up — it's a **lead moderator
+ N personas + N rounds** pipeline that's designed to push past the
filler answers a single LLM gives by default ("consult an advisor",
"consider diversification", "research the market").

## TL;DR

```bash
# Simplest — defaults to 2 rounds, current model for everyone
/brainstorm Should we migrate from Postgres to ClickHouse for analytics?

# All flags
/brainstorm --rounds 3 --lead claude-opus-4-7 \
            --models gpt-5,nim/deepseek-ai/deepseek-r1,qwen/qwen-max \
            Pick the 5 most likely high-return US tech stocks for 2026
```

You can also invoke it from the SSJ menu (`/ssj` → 1 (Brainstorm))
which prompts you for the agent count and rounds interactively.

The output lives at `brainstorm_outputs/brainstorm_<timestamp>.md` plus
a derived `brainstorm_outputs/todo_list.txt` that `/worker` can pick up.

## Why "moderated multi-round"?

A vanilla `/brainstorm Pick stocks` against any single LLM produces
something like `"Consider semiconductors. Diversify. Consult a
financial advisor."` — that's the model's safe-by-default mode.
Three things change that:

1. **A lead moderator** opens the debate by stating *what concrete
   artifact would make this useful* (e.g. "specific tickers with a
   thesis, not 'consider semiconductors'") and explicitly **bans the
   cheap escape hatches** ("consult an advisor", "diversify", "monitor
   regularly"). The lead enforces this throughout.

2. **Multiple rounds** of debate with personas. Round 1 is initial
   positions. Round 2+ is **adversarial cross-examination**: every
   persona MUST quote another agent's specific claim and attack it
   with a falsifiable counter-claim. Polite agreement is forbidden.
   The lead probes any persona who dodges.

3. **Lead-produced synthesis** at the end. The lead reads the whole
   transcript and writes a structured master plan with named sections
   (Consensus / Dissents / Concrete Action Plan / What Was Filler).
   This is what feeds the TODO file `/worker` consumes.

## Flags

| Flag | Default | What it does |
|---|---|---|
| `--rounds N` | `2` | Number of debate rounds. Round 1 = positions; round 2+ = adversarial. Clamp `[1, 6]`. |
| `--lead <model>` | session model | Who runs the moderator role (opening, probes, synthesis). Use a stronger model here when personas are weak. |
| `--models a,b,c` | session model | Persona models, distributed round-robin. Different families = different blind spots. |
| `--ground` (or `--ground=N`) | off | Pre-fetch a `/research` brief on the topic and inline the top results so personas cite real sources instead of hallucinating from training memory. Bare `--ground` = top 15. `--ground=N` = top N (clamped to 3-50). Costs 10-30s for the fetch. Cached for 24h, so back-to-back runs on the same topic are basically free. |

All three flags compose. Order doesn't matter. A flag can sit before
the topic, after the topic, or in the middle:

```bash
/brainstorm --rounds 3 redesign auth flow --lead claude-opus-4-7
/brainstorm redesign auth flow --models gpt-5,deepseek-r1 --rounds 2
```

## What the rounds look like

### Round 1 — initial positions
Each persona stakes their position with 3-5 concrete actionable
points, prefixed with their identity (`[Agent A — Sarah, Quantitative
Analyst]`). They see the lead's opening framing as the "debate anchor"
they must adhere to.

### Round 2+ — adversarial cross-examination
Same personas, but the system prompt completely changes. Each persona
is required to:

1. Quote a specific claim from another agent verbatim (by letter).
2. Attack a specific weakness (data wrong / mechanism doesn't produce
   outcome / confounder ignored / un-falsifiable / contradicts a
   stronger claim already made).
3. Propose a falsifiable counter-claim with a specific number, date,
   or named entity.

Format is structured so weak models can follow it:

```markdown
### [CHALLENGE → Agent A]
> "NVDA will hit $200 by Q3 driven by AI capex"
**Why this fails:** ignores SEC overhang on insider sales + slowing
hyperscaler capex growth in 2026 H1.
**Counter:** more likely range $130-160 by Q3; falsifiable — if NVDA
closes above $180 on any day before Sept 30 I'm wrong.
```

Politeness — `"great point"`, `"I agree, and would add"`, restating
without attacking — is **explicitly forbidden** by the prompt and
specifically detected by the lead's round-2+ probe.

### Lead probes between personas
After every persona's turn (in any non-final round), the lead reads
their contribution and either replies `NO_PROBE` (good enough) or
demands a one-shot follow-up. In round 1 the probe asks for more
specificity; in round 2+ the probe asks for an actual challenge:

```
> Lead to Agent C: Agent A said "NVDA will hit $200". Attack it or
  accept it — your call, but commit. Quote and refute, don't dodge.
```

The probed persona gets one more swing to fix it before the round
moves on.

### Final synthesis — by the lead, not the main agent
The lead reads the full transcript and produces:

```markdown
## Consensus
- Buy NVDA above $130 (backed by: A, B)
- Avoid LCID — three sources flagged the cash burn (backed by: A, C)
- ...

## Dissents
- Agent A says hold gold via GLD; Agent C says gold is dead money
  in a high-real-rate regime — bottom line: I side with C, gold is
  out unless real rates fall ≥100bp.

## Concrete Action Plan
1. Open positions on NVDA / AVGO / SMCI at next ≤2% intraday dip.
   Owner: user. Done = 3 buy orders placed.
2. ...

## What Was Filler
- Agent A's "diversify across sectors" — banned by the anchor.
- Two unsourced claims about "geopolitical tailwinds" — drop.
```

This synthesis is appended to the brainstorm `.md` file AND inlined
in the TODO-generation prompt so the main agent only needs to write
the `todo_list.txt` file (no `Read` round-trip — that pattern caused
duplicate Reads on weaker models).

## Data-hungry topics: use `--ground`

By default `/brainstorm` is **pure-reasoning** — personas have no tool
access during the debate (they run with `no_tools=True`), so they only
know what their underlying model knew at training time. That's fine
for design / architecture / strategy questions, but a problem for
anything where a useful answer depends on **fresh facts** (stocks,
current events, recent news, today's API status, etc.).

The fix is the `--ground` flag: it runs `/research` on your topic
**before** the debate starts, formats the top results as a `### GROUNDING DATA`
block, and inlines that into every persona's context. The personas
are then explicitly instructed to cite results by `[N]` when their
claim relates to one — and to flag claims the data does NOT support
instead of inventing figures.

```bash
# Stocks — fetch real news / discussions before debating
/brainstorm --ground 2026 年美股哪些值得买

# Architecture comparison — fetch real benchmarks first
/brainstorm --ground=20 ClickHouse vs Pinot for our analytics

# Quick scan, top 5 only
/brainstorm --ground=5 should we rewrite our orchestrator in Rust
```

What grounding does NOT solve:
- **Specific code in a repo it hasn't read** — `/research` indexes the
  web, not your repo. For repo-specific questions, run a `/agent` on
  the relevant files first or paste them into the topic.
- **Information that doesn't exist publicly** — internal company data,
  proprietary benchmarks, etc. Won't be in any `/research` source.

The grounding fetch costs 10-30s and one network round-trip per source.
Results are cached for 24h, so back-to-back runs on the same topic are
basically free.

### Without `--ground` (the default)

`/brainstorm` without grounding still works — and is the right choice
for these topics:

| Use it for | Why |
|---|---|
| Architecture decisions ("Postgres vs ClickHouse for our analytics?") | Trade-offs are well-covered in training data; multi-persona debate surfaces angles a single model glosses over. |
| Refactor strategies ("how should we untangle the auth layer?") | Same — competing approaches and their failure modes are debatable from first principles. |
| API / UX design tensions | Multi-perspective stress-test of design choices. |
| Risk assessment of a planned change | Different personas (security, ops, product) each surface different risks. |
| Strategy / roadmap ordering | Adversarial round forces you to defend why X before Y. |

## Tips

- **Always pass `--ground` for any topic touching the real world.**
  Stocks, market data, current events, recent product releases, news,
  benchmarks — all of these get drastically better with grounding.
  Without it, personas confidently make up numbers and tickers from
  training memory. With it, every claim has to cite a source or admit
  it's speculation. The 10-30s fetch is worth it.
- **Use `--lead <strong-model>` when personas are weak.** A qwen2.5
  panel led by a Claude moderator gets far better synthesis than the
  same panel left to its own devices.
- **Use `--models` for high-stakes brainstorms.** Multi-model = real
  epistemic diversity. Three Claudes will agree with each other; a
  Claude + a GPT + a DeepSeek will surface real disagreements.
- **2 rounds is the sweet spot for most topics.** 1 round is monologues
  (no debate at all); 3 rounds is for high-stakes topics where you
  want convergence; 4-6 rounds usually just spends tokens.
- **Output file is auditable.** Every challenge, probe, and follow-up
  is recorded with the agent letter and round number — you can scroll
  back through `brainstorm_outputs/brainstorm_<ts>.md` to see exactly
  who said what.

## Implementation pointer

All in `commands/advanced.py`:

- `_parse_rounds_flag`, `_parse_lead_flag`, `_parse_models_flag`,
  `_parse_ground_flag` — flag extraction, all permissive about position.
- `_lead_opening` — the agenda-setter call (sees grounding when present).
- `_lead_probe` — round-aware (round 1 vs round 2+) dodge detector.
- `_lead_synthesis` — the four-section master plan generator (requires
  consensus claims to trace to grounding `[N]` or persona claims).
- `_fetch_grounding` / `_format_grounding_brief` — research aggregator
  call + compact markdown formatter for the grounding block.
- `cmd_brainstorm` — wires it all together.

Tests in `tests/test_brainstorm_lead.py`,
`tests/test_brainstorm_models_flag.py`, and
`tests/test_brainstorm_grounding.py`.
