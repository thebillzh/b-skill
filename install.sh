#!/usr/bin/env bash
# Install b-skills skills, codex-only skills, and optional Claude-to-Codex mirrors.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
AGENTS_SKILLS_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
CODEX_SKILLS_DIR="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"
MIRROR_CLAUDE=0
UNINSTALL=0

usage() {
  cat <<'USAGE'
Usage: ./install.sh [--mirror-claude] [--uninstall]

Options:
  --mirror-claude  Mirror non-toolkit ~/.claude/skills entries into ~/.agents/skills.
  --uninstall      Remove toolkit-installed symlinks from all skills dirs and exit.
  -h, --help       Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mirror-claude)
      MIRROR_CLAUDE=1
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# Resolve a symlink's readlink target to an absolute path (a relative target
# is joined against the symlink's own directory). Works on broken symlinks
# too, since only the recorded target string is resolved, not the target
# itself.
link_target() {
  local link="$1"
  local target
  target="$(readlink "$link")" || return 1
  if [[ "$target" != /* ]]; then
    local dir
    dir="$(cd "$(dirname "$link")" && pwd)" || return 1
    target="$dir/$target"
  fi
  printf '%s\n' "$target"
}

# True if $1 is a symlink whose target resolves inside this repo ($ROOT).
link_target_in_root() {
  local target
  target="$(link_target "$1")" || return 1
  case "$target" in
    "$ROOT"|"$ROOT"/*) return 0 ;;
    *) return 1 ;;
  esac
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  for dir in "$CLAUDE_SKILLS_DIR" "$AGENTS_SKILLS_DIR" "$CODEX_SKILLS_DIR"; do
    [[ -d "$dir" ]] || continue
    for entry in "$dir"/*; do
      [[ -L "$entry" ]] || continue
      link_target_in_root "$entry" || continue
      rm -f "$entry"
      echo "  remove: $entry"
    done
  done
  echo "Done. b-skills symlinks removed."
  exit 0
fi

mkdir -p "$CLAUDE_SKILLS_DIR" "$AGENTS_SKILLS_DIR" "$CODEX_SKILLS_DIR"

resolve_dir() { (cd "$1" && pwd -P); }

resolved_claude="$(resolve_dir "$CLAUDE_SKILLS_DIR")"
resolved_agents="$(resolve_dir "$AGENTS_SKILLS_DIR")"
resolved_codex="$(resolve_dir "$CODEX_SKILLS_DIR")"

if [[ "$resolved_claude" == "$resolved_agents" ]]; then
  echo "Error: CLAUDE_SKILLS_DIR and AGENTS_SKILLS_DIR both resolve to $resolved_claude" >&2
  exit 2
elif [[ "$resolved_claude" == "$resolved_codex" ]]; then
  echo "Error: CLAUDE_SKILLS_DIR and CODEX_SKILLS_DIR both resolve to $resolved_claude" >&2
  exit 2
elif [[ "$resolved_agents" == "$resolved_codex" ]]; then
  echo "Error: AGENTS_SKILLS_DIR and CODEX_SKILLS_DIR both resolve to $resolved_agents" >&2
  exit 2
fi

AI_TOOLKIT_SKILLS=()
CODEX_ONLY_SKILLS=()
AGENTS_LINKED=()
CODEX_LINKED=()

link_dir() {
  local target="$1"
  local dest="$2"
  if [[ -e "$dest" && ! -L "$dest" ]]; then
    echo "  skip: refusing to overwrite non-symlink $dest" >&2
    return 1
  fi
  rm -f "$dest"
  ln -s "$target" "$dest"
}

has_name() {
  local needle="$1"
  shift || true
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

if [[ -d "$ROOT/skills" ]]; then
  for d in "$ROOT"/skills/*/; do
    [[ -d "$d" ]] || continue
    AI_TOOLKIT_SKILLS+=("$(basename "$d")")
  done
fi

if [[ -d "$ROOT/codex-skills" ]]; then
  for d in "$ROOT"/codex-skills/*/; do
    [[ -d "$d" ]] || continue
    CODEX_ONLY_SKILLS+=("$(basename "$d")")
  done
fi

for d in "$ROOT"/skills/*/; do
  [[ -d "$d" ]] || continue
  name="$(basename "$d")"
  if link_dir "$d" "$CLAUDE_SKILLS_DIR/$name"; then
    echo "  skill: $name (claude)"
  fi
  if link_dir "$d" "$AGENTS_SKILLS_DIR/$name"; then
    echo "  skill: $name (agents)"
  fi
  AGENTS_LINKED+=("$name")
done

for d in "$ROOT"/codex-skills/*/; do
  [[ -d "$d" ]] || continue
  name="$(basename "$d")"
  if link_dir "$d" "$CODEX_SKILLS_DIR/$name"; then
    echo "  skill: $name (codex-only)"
  fi
  CODEX_LINKED+=("$name")
done

if [[ "$MIRROR_CLAUDE" -eq 1 ]]; then
  for d in "$CLAUDE_SKILLS_DIR"/*; do
    [[ -e "$d" ]] || continue
    name="$(basename "$d")"
    [[ "$name" == ".DS_Store" ]] && continue
    has_name "$name" "${AI_TOOLKIT_SKILLS[@]:-}" && continue
    has_name "$name" "${CODEX_ONLY_SKILLS[@]:-}" && continue
    if link_dir "$d" "$AGENTS_SKILLS_DIR/$name"; then
      echo "  skill: $name (agents mirror)"
    fi
    AGENTS_LINKED+=("$name")
  done
fi

for name in "${AGENTS_LINKED[@]:-}"; do
  path="$CODEX_SKILLS_DIR/$name"
  if [[ -L "$path" ]] && ! has_name "$name" "${CODEX_LINKED[@]:-}" && link_target_in_root "$path"; then
    rm -f "$path"
    echo "  prune: $name (codex mirror)"
  fi
done

for dir in "$CLAUDE_SKILLS_DIR" "$AGENTS_SKILLS_DIR" "$CODEX_SKILLS_DIR"; do
  for entry in "$dir"/*; do
    [[ -L "$entry" && ! -e "$entry" ]] || continue
    link_target_in_root "$entry" || continue
    rm -f "$entry"
    echo "  prune: $(basename "$entry") (broken symlink in $(basename "$dir"))"
  done
done

echo "Done. b-skills installed."
