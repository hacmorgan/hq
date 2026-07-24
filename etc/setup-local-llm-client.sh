#!/usr/bin/env bash

# Setup script for local LLM client on leroy
# This configures the pi agent harness with a local Ollama setup via litellm proxy

set -e

echo "Setting up local LLM client..."

# Check if we're running on leroy or locally
if [[ "$(hostname)" == "leroy" ]]; then
    echo "Running directly on leroy"
    TARGET_HOST="localhost"
else
    echo "Running on different host, connecting to leroy"
    TARGET_HOST="leroy"
fi

# Install pi agent if not already installed
if ! command -v pi &> /dev/null; then
    echo "Installing pi agent..."
    # We'll use the standard setup approach for now
    pip install --user @earendil-works/pi-coding-agent
fi

# Create pi agent directory structure if needed
mkdir -p ~/.pi/agent/extensions
mkdir -p ~/.pi/agent/skills

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

# Create auto-continue-compaction.ts extension file
cat > ~/.pi/agent/extensions/auto-continue-compaction.ts << 'EOF'
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default async function (pi: ExtensionAPI) {
  // This extension makes Pi's auto-compaction self-continuing, gated by two
  // markers it makes the model self-report in every compaction summary:
  // ~Status: COMPLETE|IN_PROGRESS|BLOCKED~ (don't invent busywork once done)
  // and ~Deviation Check: ON_TRACK|DEVIATED~ (stop instead of blindly continuing
  // a confused/looping run). Verified: markers generate correctly, and the
  // "don't continue when COMPLETE" safety valve works. Not fully verified:
  // the actual IN_PROGRESS auto-continue round-trip in live interactive use
  // (only confirmed the mechanism executes; couldn't observe it end-to-end
  // via scripted -p mode, which exits before the follow-up message can run).
  pi.addCallback("compaction", async function (msg) {
    const summary = msg.summary;
    if (!summary) return;

    // Check for completion markers in the compaction summary
    const statusMatch = summary.match(/Status:\s*(COMPLETE|IN_PROGRESS|BLOCKED)/i);
    const deviationMatch = summary.match(/Deviation Check:\s*(ON_TRACK|DEVIATED)/i);

    if (statusMatch && statusMatch[1] === "COMPLETE") {
      // Don't continue when complete
      return;
    }

    if (deviationMatch && deviationMatch[1] === "DEVIATED") {
      // Don't continue when deviated
      return;
    }

    // If we get here, continue the conversation as normal
    return true;
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

echo "Local LLM client setup complete!"