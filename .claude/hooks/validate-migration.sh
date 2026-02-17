#!/bin/bash
# Prevents modification of existing migrations (must create new ones instead)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" == *"migrations/"* ]]; then
  if git ls-files --error-unmatch "$FILE_PATH" 2>/dev/null; then
    echo "BLOCKED: Do not modify existing migrations. Create a new migration instead." >&2
    exit 2
  fi
fi

exit 0
