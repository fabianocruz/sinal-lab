#!/bin/bash
# Blocks edits to sensitive files (.env, credentials, secrets)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROTECTED=(".env" ".env.local" ".env.production" "secrets" "credentials" ".claude/settings.local.json")

for pattern in "${PROTECTED[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "BLOCKED: $FILE_PATH is a protected file. Do not modify credentials." >&2
    exit 2
  fi
done

exit 0
