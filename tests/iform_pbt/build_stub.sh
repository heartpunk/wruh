#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  printf 'usage: %s TARGET_HEX OUTPUT_ELF [CONTINUATION_HEX]\n' "$0" >&2
  exit 2
fi

target_hex=${1,,}
output=$2
continuation_hex=${3:-}
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

emit_bytes() {
  local hex=$1 path=$2
  if [[ ! $hex =~ ^([[:xdigit:]]{2})+$ ]]; then
    printf 'expected a nonempty, even-length hexadecimal byte string\n' >&2
    return 2
  fi
  : > "$path"
  for ((i = 0; i < ${#hex}; i += 2)); do
    printf '.byte 0x%s\n' "${hex:i:2}" >> "$path"
  done
}

emit_bytes "$target_hex" "$work_dir/instruction-bytes.inc"
if [[ -n $continuation_hex ]]; then
  continuation_hex=${continuation_hex,,}
  emit_bytes "$continuation_hex" "$work_dir/continuation-bytes.inc"
else
  : > "$work_dir/continuation-bytes.inc"
fi

cp "$source_dir/stub.S" "$work_dir/stub.S"
(cd -- "$work_dir" && as --64 -o stub.o stub.S)
mkdir -p "$(dirname -- "$output")"
ld --build-id=none -Ttext=0x400170 -e wruh_pbt_target \
  -o "$output" "$work_dir/stub.o"
