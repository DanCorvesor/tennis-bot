#!/bin/bash
set -eo pipefail

###############################################################################
# ralph-parallel.sh
#
# Runs Claude on issues in parallel using git worktrees, respecting the
# dependency graph parsed from each issue's "Blocked by" section.
# Each completed issue pushes its branch and raises a PR via `gh`.
#
# Usage: ./scripts/ralph-parallel.sh [--max-parallel N] [--dry-run]
#
#   --max-parallel N   Max concurrent workers (default: 4)
#   --dry-run          Print the execution plan without running anything
###############################################################################

REPO_ROOT=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)
ISSUES_DIR="$REPO_ROOT/issues"
WORKTREES_DIR="$REPO_ROOT/../tennis-bot2-worktrees"
STATE_DIR=$(mktemp -d)
LOG_DIR="$REPO_ROOT/logs"
BASE_BRANCH="main"
MAX_PARALLEL=4
DRY_RUN=false

trap 'cleanup' EXIT

# --- Argument parsing --------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case $1 in
    --max-parallel) MAX_PARALLEL="$2"; shift 2 ;;
    --dry-run)      DRY_RUN=true; shift ;;
    *)              echo "Unknown option: $1"; exit 1 ;;
  esac
done

# --- Helpers -----------------------------------------------------------------

log() {
  local issue="$1"; shift
  echo "[$(date '+%H:%M:%S')] [$issue] $*"
}

cleanup() {
  # Remove all worktrees created by this run
  if [ -d "$WORKTREES_DIR" ]; then
    for wt in "$WORKTREES_DIR"/*/; do
      [ -d "$wt" ] && git -C "$REPO_ROOT" worktree remove --force "$wt" 2>/dev/null || true
    done
    rmdir "$WORKTREES_DIR" 2>/dev/null || true
  fi
  rm -rf "$STATE_DIR"
}

# Get all numbered issue files (excludes prd.md)
get_issue_files() {
  ls "$ISSUES_DIR"/[0-9]*.md 2>/dev/null | sort
}

# Extract issue key from filepath: issues/001-foo-bar.md → 001-foo-bar
issue_key() {
  basename "$1" .md
}

# Parse blocker keys from an issue file
get_blockers() {
  local file="$1"
  grep -o 'Blocked by `issues/[^`]*`' "$file" 2>/dev/null \
    | sed 's/Blocked by `issues\///; s/\.md`//' \
    || true
}

# Read state for an issue key
get_state() {
  cat "$STATE_DIR/$1" 2>/dev/null || echo "unknown"
}

# Count how many issues are in a given state
count_state() {
  grep -rl "^$1$" "$STATE_DIR"/ 2>/dev/null | wc -l | tr -d ' '
}

# Count running workers
running_count() {
  count_state "running"
}

# Check if all blockers for an issue are done
is_ready() {
  local key="$1"
  local file="$ISSUES_DIR/$key.md"
  local blockers
  blockers=$(get_blockers "$file")

  if [ -z "$blockers" ]; then
    return 0
  fi

  for blocker in $blockers; do
    if [ "$(get_state "$blocker")" != "done" ]; then
      return 1
    fi
  done
  return 0
}

# --- Worker: runs a single issue in a worktree ------------------------------

run_issue() {
  local key="$1"
  local issue_file="$ISSUES_DIR/$key.md"
  local branch="issue/$key"
  local worktree_path="$WORKTREES_DIR/$key"
  local logfile="$LOG_DIR/$key.log"

  echo "running" > "$STATE_DIR/$key"
  log "$key" "Starting"

  mkdir -p "$LOG_DIR"

  {
    # Determine base: merge all blocker branches if they exist
    local blockers
    blockers=$(get_blockers "$issue_file")

    # Create worktree from base branch
    git -C "$REPO_ROOT" worktree add "$worktree_path" -b "$branch" "$BASE_BRANCH" 2>&1

    # Merge blocker branches into the worktree so we have their changes
    if [ -n "$blockers" ]; then
      for blocker in $blockers; do
        local blocker_branch="issue/$blocker"
        if git -C "$worktree_path" rev-parse --verify "origin/$blocker_branch" >/dev/null 2>&1; then
          log "$key" "Merging dependency: $blocker_branch"
          git -C "$worktree_path" merge "origin/$blocker_branch" --no-edit 2>&1
        elif git -C "$worktree_path" rev-parse --verify "$blocker_branch" >/dev/null 2>&1; then
          log "$key" "Merging dependency (local): $blocker_branch"
          git -C "$worktree_path" merge "$blocker_branch" --no-edit 2>&1
        else
          log "$key" "Warning: blocker branch $blocker_branch not found, continuing without it"
        fi
      done
    fi

    # Build the prompt
    local issue_content
    issue_content=$(cat "$issue_file")
    local prompt=""
    if [ -f "$REPO_ROOT/ralph/prompt.md" ]; then
      prompt=$(cat "$REPO_ROOT/ralph/prompt.md")
    fi

    local commits
    commits=$(git -C "$worktree_path" log -n 5 --format="%H%n%ad%n%B---" --date=short 2>/dev/null || echo "No commits found")

    # Run Claude in the worktree
    log "$key" "Running Claude..."
    docker sandbox run claude "$worktree_path" -- \
      --verbose \
      --print \
      "You are working on issue: $key

Issue details:
$issue_content

Recent commits for context:
$commits

$prompt"

    # Stage, commit, push
    if [ -n "$(git -C "$worktree_path" status --porcelain)" ]; then
      git -C "$worktree_path" add -A 2>&1
      git -C "$worktree_path" commit -m "$(cat <<EOF
Implement $key

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)" 2>&1

      git -C "$worktree_path" push -u origin "$branch" 2>&1
      log "$key" "Pushed branch: $branch"

      # Determine PR base — if single blocker, target its branch; otherwise target main
      local pr_base="$BASE_BRANCH"
      local blocker_count
      blocker_count=$(echo "$blockers" | wc -w | tr -d ' ')
      if [ "$blocker_count" -eq 1 ]; then
        pr_base="issue/$blockers"
      fi

      # Create PR
      local pr_title
      pr_title=$(echo "$key" | sed 's/^[0-9]*-//; s/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')
      gh pr create \
        --repo "$(git -C "$REPO_ROOT" remote get-url origin | sed 's/.*://; s/\.git$//')" \
        --head "$branch" \
        --base "$pr_base" \
        --title "$pr_title" \
        --body "$(cat <<PREOF
## Issue

Implements \`issues/$key.md\`

## Details

$(grep -A 100 '## What to build' "$issue_file" | grep -B 100 '## Acceptance criteria' | head -n -1)

---
Generated by ralph-parallel.sh
PREOF
)" 2>&1

      log "$key" "PR created targeting $pr_base"
    else
      log "$key" "No changes produced — skipping PR"
    fi

    # Clean up worktree
    git -C "$REPO_ROOT" worktree remove --force "$worktree_path" 2>&1 || true

    echo "done" > "$STATE_DIR/$key"
    log "$key" "Complete"

  } > "$logfile" 2>&1 || {
    echo "failed" > "$STATE_DIR/$key"
    log "$key" "FAILED — see $logfile"
  }
}

# --- Dry run: print execution plan -------------------------------------------

print_plan() {
  echo "=== Execution Plan ==="
  echo ""
  echo "Dependency graph:"
  for file in $(get_issue_files); do
    local key
    key=$(issue_key "$file")
    local blockers
    blockers=$(get_blockers "$file")
    if [ -z "$blockers" ]; then
      echo "  $key → (no blockers, starts immediately)"
    else
      echo "  $key → blocked by: $blockers"
    fi
  done
  echo ""
  echo "Parallel groups (max $MAX_PARALLEL concurrent):"

  # Simulate execution
  local sim_done=""
  local round=1
  while true; do
    local batch=""
    for file in $(get_issue_files); do
      local key
      key=$(issue_key "$file")
      # Skip if already done
      echo "$sim_done" | grep -qw "$key" && continue
      # Skip if already in this batch
      echo "$batch" | grep -qw "$key" && continue
      # Check blockers
      local ready=true
      local blockers
      blockers=$(get_blockers "$file")
      for blocker in $blockers; do
        if ! echo "$sim_done" | grep -qw "$blocker"; then
          ready=false
          break
        fi
      done
      if $ready; then
        batch="$batch $key"
      fi
    done

    if [ -z "$batch" ]; then
      break
    fi

    echo "  Round $round:$batch"
    sim_done="$sim_done $batch"
    round=$((round + 1))
  done
  echo ""
  echo "Total rounds: $((round - 1))"
}

# --- Main loop ---------------------------------------------------------------

main() {
  echo "=== ralph-parallel ==="
  echo "Repo:         $REPO_ROOT"
  echo "Max parallel: $MAX_PARALLEL"
  echo "Worktrees:    $WORKTREES_DIR"
  echo "Logs:         $LOG_DIR"
  echo ""

  # Initialize state for all issues
  for file in $(get_issue_files); do
    local key
    key=$(issue_key "$file")
    echo "pending" > "$STATE_DIR/$key"
  done

  local total
  total=$(get_issue_files | wc -l | tr -d ' ')

  if $DRY_RUN; then
    print_plan
    exit 0
  fi

  mkdir -p "$WORKTREES_DIR" "$LOG_DIR"

  # Ensure we're up to date
  git -C "$REPO_ROOT" fetch origin 2>/dev/null || true

  while true; do
    local done_count
    done_count=$(count_state "done")
    local failed_count
    failed_count=$(count_state "failed")
    local running
    running=$(running_count)

    # Check if we're finished
    if [ $((done_count + failed_count)) -eq "$total" ]; then
      echo ""
      echo "=== All issues processed ==="
      echo "Done:   $done_count / $total"
      echo "Failed: $failed_count / $total"
      if [ "$failed_count" -gt 0 ]; then
        echo ""
        echo "Failed issues:"
        for file in $(get_issue_files); do
          local key
          key=$(issue_key "$file")
          if [ "$(get_state "$key")" = "failed" ]; then
            echo "  - $key (log: $LOG_DIR/$key.log)"
          fi
        done
      fi
      break
    fi

    # Launch ready issues up to max parallel
    for file in $(get_issue_files); do
      local key
      key=$(issue_key "$file")

      [ "$(get_state "$key")" != "pending" ] && continue
      [ "$(running_count)" -ge "$MAX_PARALLEL" ] && break

      if is_ready "$key"; then
        run_issue "$key" &
      fi
    done

    # Wait for any child to finish before re-checking
    sleep 5
  done

  wait
}

main
