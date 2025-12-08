import random
import pygame
import chessformer
from minimax import Minimax
from engine import Move, Board

# Interface
class Agent:
    def get_move(self, board):
        """Trả về nước đi (Move Object) hoặc None"""
        raise NotImplementedError

    def is_human(self):
        return False

class HumanAgent(Agent):
    def get_move(self, board):
        return None # chờ UI click
    
    def is_human(self):
        return True

class RandomAgent(Agent):
    def get_move(self, board):
        valid_moves = board.get_valid_moves()
        if not valid_moves:
            return None
        return random.choice(valid_moves)

class MinimaxAgent(Agent):
    def __init__(self, depth=3):
        self.ai = Minimax(depth=depth)

    def get_move(self, board):
        return self.ai.get_best_move(board)

# Placeholder
class MLAgent(Agent):
    def __init__(self, model_path=None):
        # self.model = load_model(model_path)
        pass

    def get_move(self, board):
        uci_str = chessformer.get_smart_move(board.fen())
        return Move.from_uci(uci_str, board)