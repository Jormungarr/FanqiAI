"""API 冒烟测试:新对局 -> 玩家翻子 -> AI 回应 -> 查询合法走法"""
import json
import urllib.error
import urllib.request

BASE = 'http://localhost:8000'


def call(path, body=None):
    data = json.dumps(body or {}).encode('utf-8') if body is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8'))


s = call('/api/new', {'agent': 'prefer'})
assert len(s['board']) == 32, 'board length'
assert s['human_color'] in ('R', 'B'), 'human color'
assert s['turn'] in ('R', 'B'), 'turn'
print(f"new: human={s['human_color']} turn={s['turn']} over={s['over']} history={len(s['history'])}")

# 找第一个暗棋翻
idx = next(i for i, c in enumerate(s['board']) if c == 'H')
m = call('/api/move', {'action': ['flip', idx]})
assert not m['over'], 'game should continue'
assert m['turn'] == m['human_color'], 'turn back to human after AI reply'
assert len(m['history']) >= 2, 'player + AI steps recorded'
print('move: flip', idx)
for h in m['history']:
    print('  step:', h['text'], '|', h['reason'])

# 每次翻棋都应记录翻出的棋子
flip_steps = [h for h in m['history'] if h['action'] and h['action'][0] == 'flip']
assert flip_steps, 'should have flip steps'
assert all(h.get('revealed') for h in flip_steps), 'every flip must record revealed piece'
print('flip reveal record OK:', [h['revealed'] for h in flip_steps])

# 玩家己方明棋的合法走法
src = next(i for i, c in enumerate(m['board'])
           if isinstance(c, str) and c.startswith(m['human_color'] + ':'))
l = call('/api/legal', {'src': src})
print(f"legal for src={src}: {len(l['moves'])} moves ->", l['moves'][:5])
assert l['ok'] is True

# 非法走法应被拒绝:重复翻同一个已翻开的子
bad = call('/api/move', {'action': ['flip', idx]})
assert 'error' in bad, 'should reject invalid flip'
print('invalid move guard OK:', bad['error'])

# 决策建议接口(仅玩家回合可调)
if m['turn'] == m['human_color']:
    adv = call('/api/advise', {})
    assert adv.get('ok'), f'advise should succeed: {adv}'
    assert adv['moves'], 'advise should return ranked moves'
    assert 0 <= adv['moves'][0]['win_rate'] <= 1, 'win_rate in [0,1]'
    assert adv['total'] > 0, 'total simulations > 0'
    print('advise OK: 推荐', adv['moves'][0]['text'],
          '胜率', round(adv['moves'][0]['win_rate'], 3),
          '| 候选', len(adv['moves']), '| 模拟', adv['total'])
else:
    print('advise skipped: not human turn')

print('ALL SMOKE TESTS PASSED')
