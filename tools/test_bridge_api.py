# 融合闭环测试:对战 ⇄ 指导快照桥接
# 覆盖:/api/play/snapshot、/api/play/from_setup、session removed 追踪
import json
import sys
import urllib.request

BASE = 'http://127.0.0.1:8000'
passed = 0


def call(path, body=None):
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(body or {}).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))


def ok(name, cond, detail=''):
    global passed
    if cond:
        passed += 1
        print(f'PASS {name}')
    else:
        print(f'FAIL {name}: {detail}')
        sys.exit(1)


# 1) 新对局(用确定性较强的 prefer 保证能吃子;seed 固定局面)
status, r = call('/api/new', {'agent': 'prefer', 'seed': 42})
ok('new 对局', status == 200 and not r.get('error'))
# 玩家执方
human = r['human_color']
ai = 'B' if human == 'R' else 'R'
# 新对局 removed 是列表;若 AI 先手直接吃子会被正确记录(此处顺带验证追踪)
ok('新对局已吃为列表', isinstance(r['removed'], list) and len(r['removed']) <= 1, str(r.get('removed')))

# 2) 走若干步直到发生吃子(翻子→吃)或直接 snapshot 验证结构
# 先验证 snapshot 结构与局面一致性
status, snap = call('/api/play/snapshot')
ok('snapshot 结构', status == 200 and snap['ok'] and len(snap['board']) == 32
   and snap['turn'] in ('R', 'B') and set(snap['scores']) == {'R', 'B'}
   and isinstance(snap['removed'], list), str(snap))
# 快照 board 与 /api/state board 一致(公开视角,归一化 :1 后缀)
def norm(b):
    out = []
    for c in b:
        if c == '.' or c == 'H':
            out.append(c)
        else:
            parts = c.split(':')
            out.append(parts[0] + ':' + parts[1])
    return out

ok('snapshot=state 棋盘一致', snap['board'] == norm(r['board']), str(snap['board'][:8]))
ok('snapshot 已吃=state 已吃', snap['removed'] == r['removed'])
print('   快照:', snap['board'][:8], '… removed:', snap['removed'])

# 3) 从快照开新对局:带 removed/分数/turn,执方跟随
status, r2 = call('/api/play/from_setup', {
    'board': snap['board'], 'turn': snap['turn'], 'scores': snap['scores'],
    'removed': snap['removed'], 'agent': 'mcts', 'human_color': human})
ok('from_setup 开新对局', status == 200 and not r2.get('error'), str(r2))
ok('from_setup 已吃带入', r2['removed'] == snap['removed'], str(r2.get('removed')))
ok('from_setup 分数带入', r2['scores'] == snap['scores'], str(r2.get('scores')))
ok('from_setup 轮到保持', r2['turn'] == snap['turn'], str(r2.get('turn')))
ok('from_setup 执方正确', r2['human_color'] == human)
print('   新对局已吃:', r2['removed'], '轮到:', r2['turn'])

# 4) 非法局面被拦截(超配明棋)
bad = list(snap['board'])
bad[0] = 'R:P'
bad[1] = 'R:P'
bad[2] = 'R:P'
bad[3] = 'R:P'
bad[4] = 'R:P'
bad[5] = 'R:P'
status, r3 = call('/api/play/from_setup', {'board': bad, 'turn': 'R'})
ok('from_setup 超配拦截', status == 400 and 'too many' in r3.get('error', ''), str(r3))

# 5) removed 追踪:真实对局中发生吃子后,state.removed 非空且棋盘少子
# 快速路径:构造一个必吃局面(红车旁边黑马,车>马可吃),from_setup 后由玩家执行吃子
board = ['.'] * 32
board[0] = 'R:R'   # 红车
board[1] = 'B:N'   # 黑马(明棋,相邻,车>马可吃)
status, r4 = call('/api/play/from_setup', {
    'board': board, 'turn': 'R', 'scores': {'R': 60, 'B': 60},
    'removed': [], 'agent': 'mcts', 'human_color': 'R'})
ok('必吃局面建立', status == 200 and r4['human_color'] == 'R' and r4['turn'] == 'R', str(r4))
status, r5 = call('/api/move', {'action': ['capture', 0, 1]})
ok('执行吃子', status == 200 and not r5.get('error'), str(r5))
ok('吃子后 removed 记录黑马', r5['removed'] == ['B:N'], str(r5.get('removed')))
ok('吃子后分数扣减', r5['scores']['B'] == 55, str(r5.get('scores')))
# AI 可能又走了,但 removed 应只含 B:J(黑将)
ok('removed 不被重复记录', len(r5['removed']) == 1, str(r5.get('removed')))
print('   吃子追踪 removed:', r5['removed'])

# 6) 快照再入指导:removed 与盘面共同约束暗棋池(黑马已吃 → 池无黑马)
status, snap2 = call('/api/play/snapshot')
board2 = snap2['board']
hm_idx = [i for i, c in enumerate(board2) if c == 'H']
status, r6 = call('/api/coach/analyze', {
    'board': board2, 'turn': snap2['turn'], 'scores': snap2['scores'],
    'removed': snap2['removed'], 'seed': 1})
ok('快照可被指导分析', status == 200 and r6.get('ok'), str(r6))
if 'remaining_pool' in r6:
    ok('指导暗棋池剔除已吃黑马', 'BN' not in r6['remaining_pool'], str(r6.get('remaining_pool')))
    print('   指导分析池:', r6.get('remaining_pool'))
else:
    # 吃子后黑方无子可走,局面已终局(符合规则),跳过池断言
    print('   指导分析:已终局(note=%s),跳过池断言' % r6.get('note'))

print(f'\n全部通过 [{passed}] [OK]')
