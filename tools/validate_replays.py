import json
import sys
from pathlib import Path

files = [
    Path('d:/workspace/game/fanqi/replay_samples/test_replay.json'),
    Path('d:/workspace/game/fanqi/replay_samples/generated_replay.json'),
    Path('d:/workspace/game/fanqi/replay_samples/generated_kifu.json'),
]

issues = []
for f in files:
    if not f.exists():
        print(f"SKIP missing: {f}")
        continue
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
    except Exception as e:
        issues.append((str(f), 'JSON_PARSE_ERROR', str(e)))
        continue
    # detect kifu format
    if isinstance(data, dict) and 'moves' in data:
        moves = data['moves']
    elif isinstance(data, list):
        moves = data
    else:
        moves = []
    for i, m in enumerate(moves):
        b = m.get('board') if isinstance(m, dict) else None
        if not isinstance(b, list):
            issues.append((str(f), i, 'board_not_list', repr(b)))
            continue
        if len(b) != 32:
            issues.append((str(f), i, 'bad_length', len(b)))
        for j, cell in enumerate(b):
            if not isinstance(cell, str):
                issues.append((str(f), i, f'cell_not_str_at_{j}', repr(cell)))
            else:
                # simple format check
                if cell != '.' and ':' not in cell:
                    issues.append((str(f), i, f'cell_malformed_at_{j}', cell))

if not issues:
    print('No issues found in scanned replay files.')
else:
    print('Found issues:')
    for it in issues:
        print(it)
