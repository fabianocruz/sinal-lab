#!/bin/bash
# Auto-formats files after editing (Python: black+isort, TS/TSX: prettier)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" == *.py ]]; then
  black "$FILE_PATH" 2>/dev/null
  isort "$FILE_PATH" 2>/dev/null
elif [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.tsx ]]; then
  npx prettier --write "$FILE_PATH" 2>/dev/null
fi

exit 0
