import argparse

try:
    from game.fanqi.engine import GameState
    from game.fanqi.ai import RandomAgent
    from game.fanqi import replay as replay_mod
except ImportError:
    # Allow running from inside the package directory, e.g.:
    #   cd game/fanqi && python simulator.py
    from engine import GameState
    from ai import RandomAgent
    import replay as replay_mod

try:
    import colorama
    colorama.init()
    HAS_COLORAMA = True
except Exception:
    HAS_COLORAMA = False

COL = {
    'R': '\x1b[31m',
    'B': '\x1b[34m',
    'RESET': '\x1b[0m'
}


def play_game(seed: int | None = None, verbose: bool = True, live: bool = False, delay: float = 0.5, vertical: bool = False):
    import os, time

    state = GameState(seed=seed)
    replay = []
    agents = {'R': RandomAgent('R', seed=seed), 'B': RandomAgent('B', seed=(None if seed is None else seed+1))}
    turn = 'R'
    ply = 0
    if verbose and not live:
        print('初始局面:')
        print(state.pretty())
        print('----')
    if live:
        clear_cmd = 'cls' if os.name == 'nt' else 'clear'
        os.system(clear_cmd)
        print('实时演示，延时：', delay)
        print(render_pretty(state, show_coords=True, vertical=vertical))
        time.sleep(delay)

    while True:
        agent = agents[turn]
        action = agent.select(state)
        if action is None:
            if verbose or live:
                print(f'{turn} 无可行动作，游戏结束')
            break
        ok, reason = state.apply_action(action)
        ply += 1
        if live:
            os.system(clear_cmd)
            print(f'{ply:03d} {turn} -> {action}  ({reason})')
            print(render_pretty(state, show_coords=True, vertical=vertical))
            print('-- scores R/B:', state.scores)
            time.sleep(delay)
        else:
            if verbose:
                print(f'{ply:03d} {turn} -> {action}  ({reason})')
                print(state.pretty())
                print('-- scores R/B:', state.scores)

        # record replay state
        replay.append({
            'player': turn,
            'action': action,
            'reason': reason,
            'scores': dict(state.scores),
            'board': replay_mod.serialize_board(state.board)
        })

        if ok:
            w = state.winner()
            if verbose or live:
                print('游戏结束, 胜者:', w)
            return w, replay
        turn = 'B' if turn == 'R' else 'R'
    return state.winner(), replay


def render_pretty(state: GameState, show_coords: bool = False, vertical: bool = False) -> str:
    lines = []
    if vertical:
        # show columns as rows (transpose 4x8 -> 8x4)
        if show_coords:
            header = '   ' + ' '.join(f'{c:2d}' for c in range(state.ROWS))
            lines.append(header)
        for c in range(state.COLS):
            row = [state.board[r*state.COLS + c] for r in range(state.ROWS)]
            cells = []
            for x in row:
                if x is None:
                    cells.append(' .')
                else:
                    if not x.revealed:
                        cells.append(' ■')
                    else:
                        txt = f"{x.color}{x.ptype}"
                        if HAS_COLORAMA or True:
                            col = COL.get(x.color, '')
                            txt = f"{col}{txt}{COL['RESET']}"
                        cells.append(f'{txt:2s}')
            prefix = f'{c:2d} ' if show_coords else ''
            lines.append(prefix + ' '.join(cells))
    else:
        if show_coords:
            header = '   ' + ' '.join(f'{c:2d}' for c in range(state.COLS))
            lines.append(header)
        for r in range(state.ROWS):
            row = state.board[r*state.COLS:(r+1)*state.COLS]
            cells = []
            for x in row:
                if x is None:
                    cells.append(' .')
                else:
                    if not x.revealed:
                        cells.append(' ■')
                    else:
                        txt = f"{x.color}{x.ptype}"
                        if HAS_COLORAMA or True:
                            col = COL.get(x.color, '')
                            txt = f"{col}{txt}{COL['RESET']}"
                        cells.append(f'{txt:2s}')
            prefix = f'{r:2d} ' if show_coords else ''
            lines.append(prefix + ' '.join(cells))
    return '\n'.join(lines)


def print_board_from_serialized(arr):
    # print 4x8 board from serialized list
    lines = []
    for r in range(4):
        row = arr[r*8:(r+1)*8]
        parts = []
        for c in row:
            if c == '.':
                parts.append(' .')
            else:
                col, ptype, rev = c.split(':')
                if rev == '0':
                    parts.append(' ■')
                else:
                    parts.append(f'{col}{ptype}')
        lines.append(' '.join(parts))
    print('\n'.join(lines))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--games', type=int, default=1)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--live', action='store_true', help='实时演示棋局（终端）')
    parser.add_argument('--delay', type=float, default=0.5, help='实时演示每步延时（秒）')
    parser.add_argument('--vertical', action='store_true', help='纵向（旋转）显示棋盘')
    parser.add_argument('--save-replay', type=str, default=None, help='保存对局为 JSON 文件（单局或使用 {i} 占位）')
    parser.add_argument('--save-kifu', type=str, default=None, help='保存对局为 kifu JSON 文件（棋谱）')
    parser.add_argument('--export-html', type=str, default=None, help='导出回放为 HTML 文件（单局或使用 {i} 占位）')
    parser.add_argument('--load-replay', type=str, default=None, help='加载已有 replay JSON，并可用 --live 或 --export-html 操作')
    args = parser.parse_args()
    results = {'R':0,'B':0,'DRAW':0,None:0}

    if args.load_replay:
        rep = replay_mod.load_replay(args.load_replay)
        if args.export_html:
            replay_mod.export_html(args.export_html, rep)
            print('已导出 HTML 到', args.export_html)
        if args.live:
            import os, time
            clear_cmd = 'cls' if os.name == 'nt' else 'clear'
            for i, s in enumerate(rep):
                os.system(clear_cmd)
                print(f"{i:03d}", s.get('player'), s.get('action'), 'scores', s.get('scores'))
                # render board
                b = s.get('board')
                # reuse render by converting to temporary GameState? simple render from string
                print_board_from_serialized(b)
                time.sleep(args.delay)
        exit(0)

    for i in range(args.games):
        winner, rep = play_game(seed=(None if args.seed is None else args.seed + i), verbose=(args.games==1 and not args.live), live=args.live, delay=args.delay, vertical=args.vertical)
        results[winner] = results.get(winner,0) + 1
        if args.save_replay:
            path = args.save_replay.format(i=i) if '{' in args.save_replay else args.save_replay
            replay_mod.save_replay(path, rep)
            print('已保存 replay 到', path)
        if args.save_kifu:
            path = args.save_kifu.format(i=i) if '{' in args.save_kifu else args.save_kifu
            replay_mod.save_kifu(path, rep, meta={'seed': args.seed, 'game_index': i, 'winner': winner})
            print('已保存 kifu 到', path)
        if args.export_html:
            path = args.export_html.format(i=i) if '{' in args.export_html else args.export_html
            replay_mod.export_html(path, rep)
            print('已导出 HTML 到', path)
    print('结果汇总:', results)


