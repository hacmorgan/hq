#!/usr/bin/env bash

# Setup script for the local LLM client: Pi (agent harness) + litellm proxy
# fronting Ollama on the LAN GPU host (192.168.0.104, Windows, qwen3-coder:30b
# / qwen2.5-coder:32b). Run this on the workstation that will run Pi - it
# does not touch the GPU host itself (see ~/notes/personal/howtos.org for
# GPU-host setup: OLLAMA_CONTEXT_LENGTH, SSH access, etc).

set -e

echo "Setting up local LLM client..."

# Install pi agent if not already installed
if ! command -v pi &> /dev/null; then
    echo "Installing pi agent..."
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent
fi

# Install the litellm proxy if not already available. This is a hard
# dependency: Pi's local-qwen provider points at the litellm proxy on
# localhost:4000 (not directly at Ollama), so without litellm installed Pi
# has nothing to connect to ("pi can't connect"). Need the [proxy] extra for
# the `litellm --config ... --port` server. Installs into whatever Python
# environment `pip` currently resolves to (e.g. an active venv).
if ! command -v litellm &> /dev/null && ! python3 -c "import litellm" &> /dev/null; then
    echo "Installing litellm proxy..."
    pip install 'litellm[proxy]'
fi

# Create pi agent directory structure if needed
mkdir -p ~/.pi/agent/extensions
mkdir -p ~/.pi/agent/skills
mkdir -p ~/tmp

# Create litellm proxy config, fronting Ollama via the ollama_chat provider.
# The tool-call-leak callback is ENABLED by default: the qwen3-coder
# Hermes-style leak (a bare <function=X><parameter=Y> text blob instead of a
# structured tool call) DOES reproduce under Pi - confirmed on pi 0.82.0,
# where a plain "run this bash command" task leaked the call as literal text
# and no tool actually ran, making Pi unusable as a coding agent. Earlier
# notes claimed the leak only happened under Claude Code's huge system
# prompt; that no longer holds. Trade-off: the callback buffers each response
# until done:true to detect the leak, so responses arrive whole rather than
# token-by-token. If you ever want streaming back and are willing to risk the
# leak, comment the two litellm_settings lines below out again.
cat > ~/tmp/litellm-config.yaml << 'EOF'
model_list:
  - model_name: qwen2.5-coder:32b
    litellm_params:
      model: ollama_chat/qwen2.5-coder:32b
      api_base: http://192.168.0.104:11434
      supports_function_calling: true
  - model_name: qwen3-coder:30b
    litellm_params:
      model: ollama_chat/qwen3-coder:30b
      api_base: http://192.168.0.104:11434
      supports_function_calling: true

# custom_callbacks.py handles qwen2.5-coder's JSON tool-call leak and
# qwen3-coder's Hermes-style <function=X><parameter=Y> leak. Enabled here
# (2026-07-25) after the qwen3-coder leak was observed reproducing under Pi
# 0.82.0 itself - a simple "run this bash command" task leaked the call as
# literal <function=bash>...</function> text and no tool ran. (An earlier
# 2026-07-24 note had disabled this, believing the leak only happened under
# Claude Code's much larger system prompt - that turned out not to hold.) The
# callback buffers every response until done:true to make leak-detection
# possible, which trades away token-by-token streaming in Pi. To get
# streaming back at the risk of the leak, comment the two lines below out.
litellm_settings:
  callbacks: custom_callbacks.proxy_handler_instance
EOF

# Create the tool-call-leak workaround itself (kept even while disabled above,
# so it's a one-line uncomment to bring back, not a rewrite).
cat > ~/tmp/custom_callbacks.py << 'EOF'
"""
Workaround for Ollama-served Qwen coder models not reliably emitting
structured tool calls under Claude Code's large multi-tool system prompt.
Instead they fall back to one of a few different text conventions they saw
in pretraining, which Ollama doesn't recognize, so litellm faithfully passes
them through as plain text instead of a structured tool call:

- qwen2.5-coder:32b: bare or <tool_call>-tag-wrapped JSON,
  {"name": ..., "arguments": ...}
- qwen3-coder:30b: Hermes/functionary-style pseudo-XML,
  <function=NAME>\n<parameter=KEY>\nVALUE\n</parameter>\n...\n</function>

This monkeypatches litellm's ollama_chat streaming chunk parser to buffer the
full assistant text for a turn (instead of forwarding it token-by-token) and,
once the turn is complete, checks whether the accumulated text matches either
convention. If so it's rewritten into a proper delta.tool_calls entry with
finish_reason="tool_calls" before litellm's Anthropic adapter translates it
for Claude Code - so Claude Code sees a real tool_use block instead of a
leaked string.

Trade-off: responses from this model are only visible once fully generated,
not token-by-token, since we can't tell whether a partial string is a tool
call until the turn ends. Not currently enabled in litellm-config.yaml (see
comment there) - kept here in case the leak resurfaces.

Note: this doesn't fix cases where the model emits a *structurally correct*
native tool call with missing/empty arguments (observed with qwen3-coder) -
that's the model failing to produce arguments at all, not a parsing gap.
"""

import json
import re
import time

from litellm._uuid import uuid
from litellm.integrations.custom_logger import CustomLogger
from litellm.llms.ollama.chat.transformation import (
    OllamaChatCompletionResponseIterator,
)
from litellm.types.utils import Delta, ModelResponseStream, StreamingChoices

_TOOL_CALL_TAG_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
_HERMES_FUNCTION_RE = re.compile(r"<function=([^>\s]+)>(.*?)</function>", re.DOTALL)
_HERMES_PARAMETER_RE = re.compile(r"<parameter=([^>\s]+)>(.*?)</parameter>", re.DOTALL)


def _extract_hermes_style_tool_calls(text: str):
    matches = _HERMES_FUNCTION_RE.findall(text)
    if not matches:
        return None

    tool_calls = []
    for name, body in matches:
        arguments = {
            key: value.strip() for key, value in _HERMES_PARAMETER_RE.findall(body)
        }
        tool_calls.append(
            {
                "id": f"call_{uuid.uuid4()}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        )
    return tool_calls or None


def _extract_json_style_tool_calls(text: str):
    tag_matches = _TOOL_CALL_TAG_RE.findall(text)
    candidates = tag_matches if tag_matches else [text]

    tool_calls = []
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        name = parsed.get("name")
        if not isinstance(name, str) or "arguments" not in parsed:
            continue
        tool_calls.append(
            {
                "id": f"call_{uuid.uuid4()}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(parsed.get("arguments") or {}),
                },
            }
        )
    return tool_calls or None


def _extract_tool_calls_from_text(raw_text: str):
    text = (raw_text or "").strip()
    if not text:
        return None

    return _extract_hermes_style_tool_calls(text) or _extract_json_style_tool_calls(
        text
    )


def _patched_chunk_parser(self, chunk: dict) -> ModelResponseStream:
    message = chunk.get("message") or {}

    if not hasattr(self, "_tool_call_leak_workaround_buffer"):
        self._tool_call_leak_workaround_buffer = ""

    reasoning_content = message.get("thinking")
    content_piece = message.get("content")
    native_tool_calls = message.get("tool_calls")

    if content_piece:
        self._tool_call_leak_workaround_buffer += content_piece

    is_done = chunk.get("done") is True

    if not is_done:
        # Buffer plain content instead of forwarding it, since a partial
        # string can't be checked for the tool-call shape yet. Reasoning
        # content and any natively-parsed tool_calls still pass through live.
        delta = Delta(
            content=None,
            reasoning_content=reasoning_content,
            tool_calls=native_tool_calls,
        )
        choices = [StreamingChoices(delta=delta)]
    else:
        finish_reason = chunk.get("done_reason") or "stop"
        synthetic_tool_calls = None
        if native_tool_calls is None:
            synthetic_tool_calls = _extract_tool_calls_from_text(
                self._tool_call_leak_workaround_buffer
            )

        if synthetic_tool_calls is not None:
            delta = Delta(content=None, tool_calls=synthetic_tool_calls)
            finish_reason = "tool_calls"
        elif native_tool_calls is not None:
            delta = Delta(content=None, tool_calls=native_tool_calls)
            finish_reason = "tool_calls"
        else:
            delta = Delta(
                content=self._tool_call_leak_workaround_buffer or None,
                reasoning_content=reasoning_content,
            )
        choices = [StreamingChoices(delta=delta, finish_reason=finish_reason)]

    return ModelResponseStream(
        id=str(uuid.uuid4()),
        object="chat.completion.chunk",
        created=int(time.time()),
        model=chunk.get("model"),
        choices=choices,
    )


OllamaChatCompletionResponseIterator.chunk_parser = _patched_chunk_parser


class ToolCallLeakWorkaroundLogger(CustomLogger):
    """No-op logger; its only job is to make litellm import this module."""


proxy_handler_instance = ToolCallLeakWorkaroundLogger()
EOF

# Create local-qwen.ts extension file
cat > ~/.pi/agent/extensions/local-qwen.ts << 'EOF'
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Points at the local litellm proxy (localhost:4000) fronting Ollama on the
// LAN GPU host (192.168.0.104). See ~/tmp/litellm-config.yaml and
// ~/tmp/custom_callbacks.py for the proxy-side tool-call-leak workarounds.
export default async function (pi: ExtensionAPI) {
  pi.registerProvider("local-qwen", {
    baseUrl: "http://localhost:4000/v1",
    apiKey: "unused",
    api: "openai-completions",
    models: [
      {
        id: "qwen3-coder:30b",
        name: "Qwen3 Coder 30B (local)",
        reasoning: false,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        // Matches the host's OLLAMA_CONTEXT_LENGTH (bumped 24576 -> 32768 ->
        // 49152 -> 65536 on 2026-07-23; confirmed fully GPU-resident via
        // `ollama ps`, and load-tested with a genuine ~54K-token prompt (82%
        // of ceiling) with no error). KV cache is statically pre-allocated
        // for the full context length at model load, not grown per-request,
        // so this headroom doesn't shrink over a long conversation -
        // confirmed by measuring identical VRAM usage before/after large
        // prompts at each step. Headroom is down to ~1.6GB at this setting
        // (started at ~3.7GB at 24576) - this is treated as the stopping
        // point for now, not a value to keep pushing without re-verifying.
        // Keep this in sync with the host env var - if it's changed again
        // without updating this number, compaction's threshold math goes
        // wrong and Ollama silently truncates oversized requests into
        // empty/degenerate completions instead of erroring.
        contextWindow: 65536,
        // Raised from 8192 on 2026-07-24 after a real response got cut off
        // mid-way (stopReason "length") on a large-output task. This is a
        // self-imposed cap, not an Ollama/model limit - Ollama's num_predict
        // just gets set to whatever this is. Keep <= compaction.reserveTokens
        // in ~/.pi/agent/settings.json (bumped to 18000 alongside this), so
        // there's always room left for a full-length response even right at
        // the compaction threshold.
        maxTokens: 16000,
      },
      {
        id: "qwen2.5-coder:32b",
        name: "Qwen2.5 Coder 32B (local)",
        reasoning: false,
        input: ["text"],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 24576,
        // Deprioritized fallback (qwen3-coder is preferred). Left lower than
        // qwen3-coder's maxTokens deliberately: compaction.reserveTokens is a
        // single global Pi setting shared by both models, so bumping it for
        // qwen3-coder's larger window (18000) would leave this smaller
        // 24576-window model almost no headroom (24576-18000=6576) before
        // every response triggers compaction.
        maxTokens: 8192,
      },
    ],
  });
}
EOF

# Create auto-continue-compaction.ts extension file. Pi's threshold-triggered
# auto-compaction is deliberately non-continuing by design - it compacts then
# just stops, waiting for the user. This extension makes it self-continuing,
# gated by two markers it makes the model self-report in every compaction
# summary it generates itself (Status: COMPLETE|IN_PROGRESS|BLOCKED, and
# Deviation Check: ON_TRACK|DEVIATED), plus resumes literally from a
# maxTokens-truncated response's tail instead of a generic "keep going" nudge.
# NOTE: there is no pi.addCallback() API - the real surface is
# pi.on(eventName, handler). An earlier draft of this file used addCallback
# and would fail to load entirely ("pi.addCallback is not a function") -
# if you see that error, this heredoc is what's out of sync, not your
# ~/.pi/agent/extensions/ copy.
cat > ~/.pi/agent/extensions/auto-continue-compaction.ts << 'EOF'
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm, serializeConversation } from "@earendil-works/pi-coding-agent";
import { complete } from "@earendil-works/pi-ai/compat";

// Pi's threshold-triggered auto-compaction is deliberately non-continuing by
// design (see agent-session.js: "Threshold: Context over threshold, compact,
// NO auto-retry (user continues manually)"). Only hard context-overflow
// errors auto-retry, capped at one attempt. That means on a long unattended
// agentic run, hitting the threshold silently compacts and then just stops,
// waiting for the user to type something - which looks identical to a stall.
//
// This extension makes threshold compaction self-continuing, gated by two
// semantic checks the model itself reports in the summary it generates:
//   - Status: COMPLETE means don't invent further work once the real task
//     is done, even if that final "anything else?" turn happened to cross
//     the compaction threshold.
//   - Deviation Check: DEVIATED means the model itself noticed its recent
//     work drifted from the original goal or contradicts the previous
//     summary (e.g. a repeating failed action) - stop and let the user look,
//     rather than blindly continuing a confused loop.
// Both checks require the model to compare against preparation.previousSummary,
// which Pi already threads forward automatically across compactions - no
// separate storage needed on our side for that comparison.
//
// This bypasses Pi's own compact() and generates the summary directly (same
// pattern as Pi's bundled examples/extensions/custom-compaction.ts), rather
// than passing customInstructions through compact(). That's because
// compact()'s split-turn path (a single long turn with many tool calls - the
// common case for an unattended agentic run with only one user message) is
// generated by generateTurnPrefixSummary(), an internal function with no
// customInstructions parameter at all - our markers were silently dropped
// there in testing. Summarizing everything in one shot sidesteps that gap
// and guarantees the markers appear in every compaction, split-turn or not.
// Note: Pi's default compaction summary format has no knowledge of these
// markers at all, so a version that just inspects whatever summary Pi
// produces on its own (without generating a custom one here) will never find
// them - the custom generation isn't an optional extra, it's load-bearing.
//
// Only the "threshold" reason is touched. "manual" (/compact) and "overflow"
// (Pi's own single-retry recovery) are left completely alone.
//
// Extension API note: there is no pi.addCallback() - the real surface is
// pi.on(eventName, handler) for the fixed set of events Pi emits (verified
// against node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts).

const SUMMARY_INSTRUCTIONS = `
You are a conversation summarizer. Create a comprehensive summary of this conversation that captures:

1. The main goal and objective (the user's original request)
2. Key decisions made and their rationale
3. Important code changes, file modifications, or technical details
4. Current state of any ongoing work
5. Any blockers, issues, or open questions
6. Next steps that were planned or suggested

Be thorough but concise. The summary will replace this part of the conversation history, so include all information needed to continue the work effectively. Format as structured markdown with clear sections (e.g. Goal, Progress, Next Steps).

Additionally, insert exactly these two lines at the very top of the summary, before any other section:

## Status: COMPLETE | IN_PROGRESS | BLOCKED
## Deviation Check: ON_TRACK | DEVIATED

Status: COMPLETE means the user's original request has been fully satisfied and there is nothing further to do. IN_PROGRESS means there is remaining work toward the original request. BLOCKED means you cannot proceed without user input.

Deviation Check: compare your current understanding of the goal and recent progress against the previous session summary supplied below (if present). ON_TRACK means the work is still aligned with the original request and the previous summary. DEVIATED means you notice the recent work has drifted from the original goal, contradicts the previous summary, or shows signs of a confused or looping pattern (e.g. repeating the same failed action). If DEVIATED, add one sentence directly after the line explaining why.
`.trim();

function parseMarker(summary: string, label: string): string | undefined {
  const match = summary.match(new RegExp(`##\\s*${label}:\\s*([A-Z_]+)`, "i"));
  return match?.[1]?.toUpperCase();
}

const TRUNCATION_TAIL_CHARS = 2000;

// If the last message about to be compacted away was cut off by hitting
// maxTokens (stopReason "length"), grab its literal trailing text now, before
// it's gone. A generic "continue the remaining work" nudge built from a
// *summary* can't tell the model exactly where a truncated sentence/code
// block stopped - it just re-approaches the task from scratch. Quoting the
// literal tail lets the model resume the actual cut-off output directly.
function extractTruncatedTail(messages: readonly { role: string; stopReason?: string; content?: unknown[] }[]) {
  const last = messages[messages.length - 1];
  if (!last || last.role !== "assistant" || last.stopReason !== "length" || !Array.isArray(last.content)) {
    return undefined;
  }
  const text = last.content
    .filter((c): c is { type: "text"; text: string } => (c as { type?: string }).type === "text")
    .map((c) => c.text)
    .join("\n")
    .trim();
  if (!text) return undefined;
  return text.length > TRUNCATION_TAIL_CHARS ? text.slice(-TRUNCATION_TAIL_CHARS) : text;
}

export default async function (pi: ExtensionAPI) {
  let pendingCompactionSummary: string | undefined;
  let pendingTruncatedTail: string | undefined;

  // A genuinely new turn starting (e.g. from a queued follow-up message that
  // let the loop continue past the compaction) means the "stopped only
  // because of compaction" condition no longer applies to whatever
  // agent_settled eventually follows - clear the flag so it doesn't fire on a
  // later, unrelated settle.
  pi.on("turn_start", () => {
    pendingCompactionSummary = undefined;
    pendingTruncatedTail = undefined;
  });

  pi.on("session_before_compact", async (event, ctx) => {
    if (event.reason !== "threshold") return; // leave manual /compact and overflow recovery untouched

    const { preparation, signal } = event;
    const { messagesToSummarize, turnPrefixMessages, tokensBefore, firstKeptEntryId, previousSummary } = preparation;
    const allMessages = [...messagesToSummarize, ...turnPrefixMessages];

    // Capture this regardless of whether we go on to build a custom summary
    // below or fall back to Pi's default compaction - either way the raw
    // truncated text is about to be discarded.
    pendingTruncatedTail = extractTruncatedTail(allMessages);

    if (!ctx.model) return;

    const auth = await ctx.modelRegistry.getApiKeyAndHeaders(ctx.model);
    if (!auth.ok) return; // fall back to Pi's default compaction

    if (allMessages.length === 0) return; // nothing to summarize, fall back to default

    const previousContext = previousSummary
      ? `\n\n<previous-summary>\n${previousSummary}\n</previous-summary>`
      : "\n\n<previous-summary>\n(none - this is the first compaction this session)\n</previous-summary>";
    const conversationText = serializeConversation(convertToLlm(allMessages));

    const summaryMessages = [
      {
        role: "user" as const,
        content: [
          {
            type: "text" as const,
            text: `${SUMMARY_INSTRUCTIONS}${previousContext}\n\n<conversation>\n${conversationText}\n</conversation>`,
          },
        ],
        timestamp: Date.now(),
      },
    ];

    try {
      const response = await complete(
        ctx.model,
        { messages: summaryMessages },
        {
          apiKey: auth.apiKey,
          headers: auth.headers,
          env: auth.env,
          maxTokens: ctx.model.maxTokens > 0 ? ctx.model.maxTokens : 8192,
          signal,
        },
      );
      const summary = response.content
        .filter((c): c is { type: "text"; text: string } => c.type === "text")
        .map((c) => c.text)
        .join("\n");
      if (!summary.trim()) return; // fall back to default on empty summary

      return {
        compaction: {
          summary,
          firstKeptEntryId,
          tokensBefore,
          usage: response.usage,
        },
      };
    } catch {
      return; // fall back to Pi's default compaction on any failure
    }
  });

  pi.on("session_compact", (event) => {
    pendingCompactionSummary = event.reason === "threshold" ? event.compactionEntry.summary : undefined;
    if (event.reason !== "threshold") pendingTruncatedTail = undefined;
  });

  pi.on("agent_settled", (_event, ctx) => {
    const summary = pendingCompactionSummary;
    const truncatedTail = pendingTruncatedTail;
    pendingCompactionSummary = undefined; // consume once regardless of outcome
    pendingTruncatedTail = undefined;
    if (!summary) return;

    const status = parseMarker(summary, "Status");
    const deviation = parseMarker(summary, "Deviation Check");

    if (status === "COMPLETE") {
      return; // task's actually done - don't invent further work
    }
    if (status !== "IN_PROGRESS" && status !== "BLOCKED") {
      ctx.ui.notify(
        "Auto-compaction summary didn't include a parseable Status marker; stopping instead of auto-continuing.",
        "warning",
      );
      return;
    }
    if (deviation !== "ON_TRACK") {
      ctx.ui.notify(
        "Auto-compaction detected the agent may have deviated from the original task (or the check was unparseable); stopping for review instead of auto-continuing.",
        "warning",
      );
      return;
    }

    const nudge = truncatedTail
      ? `Your previous response was cut off because it hit the output length limit, before context was auto-compacted. Here is the literal end of what you'd written so far:\n\n<truncated-output>\n${truncatedTail}\n</truncated-output>\n\nContinue writing EXACTLY from where that leaves off - do not repeat, rewrite, or restart what's already there. If that output was actually already complete (the cut-off was only trailing prose, not mid-content), just continue with the remaining task work described in the compaction summary's Progress/Next Steps sections instead.`
      : "Context was just auto-compacted mid-task. Continue the remaining work described in the compaction summary's Progress/Next Steps sections. If you determine the task is actually already complete, say so instead of inventing further work.";

    pi.sendUserMessage(nudge);
  });
}
EOF

# Create settings.json with proper compaction settings
cat > ~/.pi/agent/settings.json << 'EOF'
{
  "lastChangelogVersion": "0.81.1",
  "theme": "dark",
  "compaction": {
    "enabled": true,
    "reserveTokens": 18000
  }
}
EOF

# Symlink Claude Code skills into Pi's shared skills dir (Pi implements the
# same open Agent Skills standard - SKILL.md + progressive disclosure - so
# no bridge/conversion needed). Defensive: skip anything not present, since
# this may run on a machine before Claude Code plugins are installed.
echo "Linking skills..."
if [[ -d ~/.claude/plugins/devtools/skills ]]; then
    for d in ~/.claude/plugins/devtools/skills/*/; do
        name=$(basename "$d")
        ln -sfn "$(readlink -f "$d")" ~/.agents/skills/"devtools-$name"
    done
fi
if [[ -d ~/.claude/plugins/mattpocock/skills ]]; then
    for pair in \
        "codebase-design:engineering/codebase-design" \
        "diagnosing-bugs:engineering/diagnosing-bugs" \
        "domain-modeling:engineering/domain-modeling" \
        "grilling:productivity/grilling" \
        "tdd:engineering/tdd"
    do
        name="${pair%%:*}"
        rel="${pair#*:}"
        src=~/.claude/plugins/mattpocock/skills/"$rel"
        [[ -d "$src" ]] && ln -sfn "$(readlink -f "$src")" ~/.agents/skills/"mattpocock-$name"
    done
fi
if [[ -d ~/.claude/skills/gitbutler ]]; then
    ln -sfn "$(readlink -f ~/.claude/skills/gitbutler)" ~/.agents/skills/gitbutler
fi

# Install a systemd --user unit so the litellm proxy comes back automatically
# on boot / after a crash, instead of being a manual `litellm ... &` that dies
# with the terminal. Only attempt this where a systemd user bus actually
# exists (skips containers/WSL-without-systemd/CI); those fall back to the
# manual command printed at the end.
PROXY_MANAGED_BY_SYSTEMD=0
if command -v systemctl &> /dev/null && systemctl --user show-environment &> /dev/null; then
    echo "Installing systemd --user unit for the litellm proxy..."

    # ExecStart needs an absolute litellm path: a --user unit does not inherit
    # the shell PATH, so a bare `litellm` (which lives in a venv here) would
    # not resolve. The console script's own shebang points back at the right
    # interpreter, so the absolute path is self-contained. Prefer `command -v`
    # (resolves the active-venv copy during setup); fall back to the bin dir of
    # whichever python can import litellm.
    LITELLM_BIN="$(command -v litellm 2>/dev/null || true)"
    if [[ -z "$LITELLM_BIN" ]]; then
        LITELLM_BIN="$(dirname "$(python3 -c 'import sys; print(sys.executable)')")/litellm"
    fi

    mkdir -p ~/.config/systemd/user
    # %h expands to $HOME inside the unit. WorkingDirectory MUST be ~/tmp so
    # litellm can import custom_callbacks.py (the tool-call-leak workaround) as
    # a local module - it's loaded by module name relative to the CWD.
    cat > ~/.config/systemd/user/litellm-proxy.service << EOF
[Unit]
Description=litellm proxy fronting Ollama for the local Pi coding agent (localhost:4000)
Documentation=file://%h/notes/personal/howtos.org
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/tmp
ExecStart=${LITELLM_BIN} --config %h/tmp/litellm-config.yaml --port 4000
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

    # Keep the proxy running when no session is logged in (headless hosts,
    # post-reboot before first login). Non-fatal if the platform disallows it.
    loginctl enable-linger "$USER" 2>/dev/null || \
        echo "  (could not enable linger - proxy will only run while you're logged in)"

    systemctl --user daemon-reload
    systemctl --user enable litellm-proxy.service > /dev/null 2>&1 || true
    # restart (not start) so re-running setup picks up any config/unit changes
    # and this is idempotent whether or not the service was already running.
    systemctl --user restart litellm-proxy.service
    PROXY_MANAGED_BY_SYSTEMD=1
else
    echo "No systemd --user bus detected - skipping proxy service install."
    echo "  Start the proxy manually instead (see Next steps below)."
fi

echo "Local LLM client setup complete!"
echo
echo "Next steps:"
if [[ "$PROXY_MANAGED_BY_SYSTEMD" == "1" ]]; then
    echo "  1. Proxy is running under systemd (auto-starts on boot):"
    echo "       systemctl --user status litellm-proxy"
    echo "       journalctl --user -u litellm-proxy -f      # logs"
else
    echo "  1. Start the proxy:  (cd ~/tmp && litellm --config ~/tmp/litellm-config.yaml --port 4000 &)"
    echo "     (run from ~/tmp so custom_callbacks.py is importable)"
fi
echo "  2. Use pi:           pi --provider local-qwen --model qwen3-coder:30b --thinking off"
echo
echo "GPU host setup (Ollama env vars, SSH access) is separate - see ~/notes/personal/howtos.org."
