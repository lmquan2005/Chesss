import random
import pygame
from minimax import Minimax

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
        print("ML Model predicting...")
        # return self.model.predict(board)
        return None