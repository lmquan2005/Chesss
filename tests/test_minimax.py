import os
import sys
import json
import random
from datetime import datetime

# Ensure project root is on sys.path so imports like `from engine import Board` work
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine import Board, Move

# Avoid importing `agents.py` here because it imports `chessformer` (and thus
# `torch`) at module import time. We create small local wrappers that replicate
# the minimal `get_move` behaviour needed for testing so the script can run
# without heavy ML dependencies.
from minimax import Minimax


class LocalMinimaxAgent:
    def __init__(self, depth=3):
        self.ai = Minimax(depth=depth)

    def get_move(self, board):
        return self.ai.get_best_move(board)


class LocalRandomAgent:
    def get_move(self, board):
        valid = board.get_valid_moves()
        if not valid:
            return None
        return random.choice(valid)


# ML agent is optional: try to import `chessformer` at runtime; if unavailable,
# we'll skip the ML matchup.
try:
    import chessformer  # may raise if torch isn't installed

    class LocalMLAgent:
        def get_move(self, board):
            uci = chessformer.get_smart_move(board.fen())
            return Move.from_uci(uci, board)

    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False


def play_game(white_agent, black_agent, max_moves=400):
    b = Board()
    moves = 0

    while moves < max_moves:
        # Terminal/draw checks
        is_draw, reason = b.is_draw()
        if is_draw:
            return "draw", reason
        if b.is_checkmate('w'):
            return "black", "checkmate"
        if b.is_checkmate('b'):
            return "white", "checkmate"

        agent = white_agent if b.turn == 'w' else black_agent

        try:
            move = agent.get_move(b)

            # If an agent returns None (shouldn't happen for non-human), pick a random legal move
            if move is None:
                valid = b.get_valid_moves()
                if not valid:
                    break
                move = random.choice(valid)

            # Validate move is legal
            valid_moves = b.get_valid_moves()

            def same_move(a, bmv):
                return a.from_sq == bmv.from_sq and a.to_sq == bmv.to_sq and a.promotion == bmv.promotion

            if not any(same_move(move, vm) for vm in valid_moves):
                # Illegal move -> current side loses
                loser = 'w' if b.turn == 'w' else 'b'
                winner = 'black' if loser == 'w' else 'white'
                return winner, 'illegal_move'

            b.apply_move(move)

        except Exception as e:
            # Agent crashed -> it loses
            winner = 'black' if b.turn == 'w' else 'white'
            return winner, f'exception:{e}'

        moves += 1

    # If loop ends by move limit or no moves, decide result
    is_draw, reason = b.is_draw()
    if is_draw:
        return "draw", reason
    if b.is_checkmate('w'):
        return "black", "checkmate"
    if b.is_checkmate('b'):
        return "white", "checkmate"

    return "draw", "max_moves_or_unknown"


def run_matchup(agent_a_ctor, agent_b_ctor, n_games=10):
    """Run n_games between agent_a and agent_b, swapping colors each game.
    agent?_ctor are callables that return a fresh Agent instance."""
    stats = {"a_wins": 0, "b_wins": 0, "draws": 0, "details": []}

    for i in range(n_games):
        # Alternate colors: even -> A=white, odd -> A=black
        if i % 2 == 0:
            white = agent_a_ctor()
            black = agent_b_ctor()
            a_is_white = True
        else:
            white = agent_b_ctor()
            black = agent_a_ctor()
            a_is_white = False

        result, reason = play_game(white, black)

        if result == 'draw':
            stats['draws'] += 1
            winner = 'draw'
        elif result == 'white':
            # Who was white this game?
            if a_is_white:
                stats['a_wins'] += 1
                winner = 'A'
            else:
                stats['b_wins'] += 1
                winner = 'B'
        elif result == 'black':
            if a_is_white:
                stats['b_wins'] += 1
                winner = 'B'
            else:
                stats['a_wins'] += 1
                winner = 'A'
        else:
            winner = 'unknown'

        stats['details'].append({
            'game': i + 1,
            'result': result,
            'reason': reason,
            'winner': winner
        })

        print(f"Game {i+1}/{n_games}: result={result}, reason={reason}, winner={winner}")

    return stats


def main():
    os.makedirs('output', exist_ok=True)

    # Minimax-only evaluation settings
    minimax_eval_games = 100

    print(f"Running Minimax (depth=2) evaluation: {minimax_eval_games} games vs Random")
    minimax_stats = run_matchup(lambda: LocalMinimaxAgent(depth=2), LocalRandomAgent, n_games=minimax_eval_games)

    # Convert to the same summary fields as the ML results format
    num_games = minimax_eval_games
    smart_wins = minimax_stats.get('a_wins', 0)
    random_wins = minimax_stats.get('b_wins', 0)
    draws = minimax_stats.get('draws', 0)
    win_rate = (smart_wins / num_games) * 100 if num_games > 0 else 0.0
    non_loss_rate = ((smart_wins + draws) / num_games) * 100 if num_games > 0 else 0.0

    minimax_result = {
        'num_games': num_games,
        'smart_wins': smart_wins,
        'random_wins': random_wins,
        'draws': draws,
        'win_rate': round(win_rate, 2),
        'non_loss_rate': round(non_loss_rate, 2)
    }

    minimax_out = os.path.join('output', 'minimax-results.json')
    with open(minimax_out, 'w', encoding='utf-8') as f:
        json.dump(minimax_result, f, ensure_ascii=False, indent=2)
    print(f"Saved Minimax evaluation to {minimax_out}")


if __name__ == '__main__':
    main()
