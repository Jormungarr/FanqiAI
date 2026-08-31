# -*- coding: utf-8 -*-
"""指导模式 /api/coach/analyze 接口测试。"""
import json
import sys
import urllib.request

BASE = 'http://localhost:8000'


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test(name, body, expect_ok=True):
    status, r = post('/api/coach/analyze', body)
    ok = (r.get('ok', False) is True) == expect_ok
    print('%s %s: status=%d ok=%s' % ('PASS' if ok else 'FAIL', name, status, r.get('ok')))
    if not ok:
        print('   response:', json.dumps(r, ensure_ascii=False)[:300])
        sys.exit(1)
    return r


# 用例A: 必赢残局——红将(0,0)明棋 vs 黑将(0,1)明棋,红先,黑只剩30分
board = ['.'] * 32
board[0] = 'R:J'
board[1] = 'B:J'
r = test('必赢残局(红将吃黑将)', {'board': board, 'turn': 'R', 'scores': {'R': 60, 'B': 30}}, True)
assert r['moves'][0]['action'][0] in ('move', 'capture') and r['moves'][0]['action'][2] == 1, '首选应为吃掉黑将'
assert r['moves'][0]['win_rate'] > 0.9, '胜率应>90%% 实际 %.1f%%' % (r['moves'][0]['win_rate'] * 100)
assert r['eval_win_rate'] is not None and r['eval_win_rate'] > 0.9, '局面胜率应>90%'
print('   首选:', r['moves'][0]['text'], '胜率 %.1f%%' % (r['moves'][0]['win_rate'] * 100),
      '| 局面胜率 %.1f%%' % (r['eval_win_rate'] * 100), '| 总模拟', r['total'])

# 用例B: 完整随机局面(32子,暗棋内容指定),黑先
pieces = []
for c in ('R', 'B'):
    for t in ('J', 'S', 'S', 'X', 'X', 'R', 'R', 'N', 'N', 'C', 'C', 'P', 'P', 'P', 'P', 'P'):
        pieces.append(c + ':' + t)
import random
random.seed(7)
random.shuffle(pieces)
board = [p + '?' for p in pieces]
for i in random.sample(range(32), 4):
    board[i] = board[i][:3]
r = test('完整随机局面(黑先)', {'board': board, 'turn': 'B', 'scores': {'R': 60, 'B': 60}}, True)
assert 1000 < r['total'] < 50000
assert r['eval_win_rate'] is not None
print('   黑方局面胜率 %.1f%% | 候选 %d 个 | 推荐: %s' % (
    r['eval_win_rate'] * 100, len(r['moves']), r['moves'][0]['text']))

# 用例C: 'H' 暗棋随机分配(5个H + 其余空) + 种子复现
board = ['.'] * 32
board[0] = 'R:J'
board[2] = 'H'
board[3] = 'H'
board[4] = 'H'
r1 = test('H随机分配(种子1)', {'board': board, 'turn': 'R', 'scores': {'R': 60, 'B': 60}, 'seed': 1}, True)
r2 = test('H随机分配(种子1复现)', {'board': board, 'turn': 'R', 'scores': {'R': 60, 'B': 60}, 'seed': 1}, True)
assert r1['moves'][0]['text'] == r2['moves'][0]['text'], '同种子应可复现'
print('   推荐(种子复现一致):', r1['moves'][0]['text'])

# 用例D: 无合法动作(全是己方明棋包围?直接空棋盘)
r = test('空棋盘(无合法动作)', {'board': ['.'] * 32, 'turn': 'R'}, True)
assert r.get('note'), '应提示已终局'
print('   note:', r['note'])

# 用例E: 非法输入
test('board长度错误', {'board': ['.'] * 31, 'turn': 'R'}, False)
test('棋子超配(3个红将)', {'board': (['R:J'] * 3) + (['.'] * 29), 'turn': 'R'}, False)
test('非法棋子类型', {'board': (['R:Z'] * 1) + (['.'] * 31), 'turn': 'R'}, False)
test('非法turn', {'board': ['.'] * 32, 'turn': 'X'}, False)

# 用例F: removed(已吃棋子)校验
board = ['.'] * 32
board[0] = 'R:J'
test('removed正常(黑将已吃)', {'board': board, 'turn': 'R', 'removed': ['B:J']}, True)
test('removed超配(2个黑将)', {'board': board, 'turn': 'R', 'removed': ['B:J', 'B:J']}, False)
test('removed非法类型', {'board': board, 'turn': 'R', 'removed': ['B:Z']}, False)
test('removed非列表', {'board': board, 'turn': 'R', 'removed': 'B:J'}, False)

print('\n全部通过 [OK]')
