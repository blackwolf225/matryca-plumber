#!/usr/bin/env bash
# Apply GitHub issue reorganization (Phases A–G). Requires gh auth with repo write scope.
set -euo pipefail

REPO="MarcoPorcellato/matryca-plumber"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BODIES="$ROOT/scripts/github-reorg/bodies"
MILESTONE_V20='v2.0.0 — Shadow DB & Safe-Sync Architecture'
MILESTONE_V196='v1.9.6 - Agent UX'

preflight() {
  if ! gh label create _write_probe --repo "$REPO" --description "probe" --color "000000" 2>/dev/null; then
    echo "ERROR: GitHub token lacks write access (403 on labels)."
    echo "Run: gh auth refresh -h github.com -s repo,project,read:org"
    echo "Then re-run: bash scripts/github-reorg/apply.sh"
    exit 1
  fi
  gh label delete _write_probe --repo "$REPO" --yes 2>/dev/null || true
}

ensure_milestone() {
  local title="$1" desc="$2"
  local num
  num=$(gh api "repos/$REPO/milestones?state=all" --jq ".[] | select(.title==\"$title\") | .number" | head -1)
  if [[ -z "$num" ]]; then
    num=$(gh api "repos/$REPO/milestones" -f title="$title" -f description="$desc" --jq '.number')
  fi
  echo "$num"
}

preflight

echo "== Phase A: labels =="
for spec in \
  "epic|Tracking issue / parent epic|3E2723" \
  "v2.0|v2.0.0 Shadow DB release track|1D76DB" \
  "core|Core daemon / graph engine|B60205" \
  "mcp|MCP server / agent tooling|5319E7" \
  "safety|Safe-Sync / data integrity|FBCA04" \
  "database|Shadow DB / storage layer|006B75" \
  "dx|Developer / operator experience|C5DEF5" \
  "agent-ux|Tier-2 agent contract / UX|D4C5F9" \
  "human-in-the-loop|Soft Gate / operator choice|F9D0C4"; do
  IFS='|' read -r name desc color <<< "$spec"
  gh label create "$name" --repo "$REPO" --description "$desc" --color "$color" 2>/dev/null || true
done

echo "== Phase B: milestones =="
M196=$(ensure_milestone "$MILESTONE_V196" 'Agent UX deliverables shipped in v1.9.5 (LLM OS Soft Gate + bootstrap_status). Tracking closure for #21 and #22.')
echo "v1.9.6 milestone: #$M196"

gh api -X PATCH "repos/$REPO/milestones/3" \
  -f title="$MILESTONE_V20" \
  -f description='Epic #20: Shadow DB read cache (shadow.sqlite, FTS5, CTEs), GraphRepository abstraction (#17), Safe-Sync write bridge for Logseq DB (#25). Agent UX (#21/#22) tracked under v1.9.6.'

echo "== Phase D: body rewrites =="
for n in 17 20 21 22 23 24 25; do
  gh issue edit "$n" --repo "$REPO" --body-file "$BODIES/issue-$n.md"
done

echo "== Phase A+B: labels and milestones =="
gh issue edit 20 --repo "$REPO" --add-label "epic,v2.0" --milestone "$MILESTONE_V20"
gh issue edit 17 --repo "$REPO" --add-label "enhancement,v2.0,core,database" --milestone "$MILESTONE_V20"
gh issue edit 23 --repo "$REPO" --add-label "enhancement,v2.0,dx" --milestone "$MILESTONE_V20"
gh issue edit 24 --repo "$REPO" --add-label "enhancement,v2.0,core,database" --milestone "$MILESTONE_V20"
gh issue edit 25 --repo "$REPO" --add-label "enhancement,v2.0,safety,mcp" --milestone "$MILESTONE_V20"

gh issue edit 21 --repo "$REPO" --add-label "documentation,enhancement,agent-ux,human-in-the-loop" --milestone "$MILESTONE_V196"
gh issue edit 22 --repo "$REPO" --add-label "enhancement,agent-ux,core,mcp" --milestone "$MILESTONE_V196"

echo "== Phase C: sub-issues of #20 =="
PARENT="I_kwDOSfr7UM8AAAABEGm6Nw"
for child in I_kwDOSfr7UM8AAAABDxVxAQ I_kwDOSfr7UM8AAAABEij64w I_kwDOSfr7UM8AAAABEikTrg I_kwDOSfr7UM8AAAABEiknWA; do
  gh api graphql -f query="mutation { addSubIssue(input: {issueId: \"$PARENT\", subIssueId: \"$child\"}) { issue { number } } }"
done

echo "== Phase B: close #21 #22 =="
gh issue comment 21 --repo "$REPO" --body "Closing as delivered in **v1.9.5** (milestone v1.9.6 - Agent UX).

Evidence: \`SYSTEM_PROMPT.md\` § LLM OS (Soft Gate + 3-option fallback), \`llms.txt\` §6, \`src/agent/mcp_server.py\` docstrings, \`src/agent/l1_memory.py\` (\`llm-os-rules.md\` seed), \`docs/openspec/llm-os-instructions.md\`, \`CHANGELOG.md\` [1.9.5]."

gh issue comment 22 --repo "$REPO" --body "Closing as delivered in **v1.9.5** (milestone v1.9.6 - Agent UX).

Evidence: \`src/graph/bootstrap_status.py\` (reads \`.matryca_daemon_state.json\`), \`bootstrap_status\` read target in \`graph_dispatch.py\` / MCP / CLI, \`tests/test_bootstrap_status.py\`, \`CHANGELOG.md\` [1.9.5]."

gh issue close 21 --repo "$REPO" --reason completed
gh issue close 22 --repo "$REPO" --reason completed

echo "== Phase G: community issues =="
gh issue edit 1 --repo "$REPO" --add-label question
gh issue comment 1 --repo "$REPO" --body "Thanks again for opening this on day one. The architectural answer stands in the thread above: Matryca preserves spatial hierarchy via BM25 page discovery + AST subtree reads rather than flat block embedding.

Closing as a resolved community question. For ongoing architecture discussion see [Discussion #19](https://github.com/MarcoPorcellato/matryca-plumber/discussions/19) and \`docs/ARCHITECTURE.md\`."
gh issue close 1 --repo "$REPO" --reason completed

gh issue comment 14 --repo "$REPO" --body "Closing with the scope split documented above:

- **Structural integrity** (404s, missing assets): Matryca Plumber — delivered in #15 (v1.9.0).
- **Semantic integrity** (\`quote_hash\` drift): Matryca Brain / Temporal Graphs — out of Plumber scope.

The claims-sidecar pattern informed our link-registry approach. For RFC-style anchoring debate, prefer [Discussion #19](https://github.com/MarcoPorcellato/matryca-plumber/discussions/19)."
gh issue close 14 --repo "$REPO" --reason completed

echo "== Phase F: GitHub Project =="
PROJECT=$(gh project create --owner MarcoPorcellato --title "v2.0 Roadmap — Shadow DB & Safe-Sync" --format json --jq '.number')
gh project link "$PROJECT" --owner MarcoPorcellato --repo "$REPO"
for n in 17 20 23 24 25; do
  gh project item-add "$PROJECT" --owner MarcoPorcellato --url "https://github.com/$REPO/issues/$n"
done
echo "Project number: $PROJECT"

echo "Done."
