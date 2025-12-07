import math
import random
import numpy as np
from PointMap import map_points, PieceMap
from engine import Move 

PIECE_VALUES = {
    'P': 10, 'N': 30, 'B': 30, 'R': 50, 'Q': 90, 'K': 900,
    'p': -10, 'n': -30, 'b': -30, 'r': -50, 'q': -90, 'k': -900
}

MAP_INDEX = {
    'P': 0, 'B': 1, 'N': 2, 'R': 3, 'Q': 4, 'K': 5,
    'p': 0, 'b': 1, 'n': 2, 'r': 3, 'q': 4, 'k': 5
}

class Minimax(object):
    def __init__(self, depth=3, AlphBetaPruning=True, UsePointMaps=True):
        self.depth = depth
        self.AlphaBetaPruning = AlphBetaPruning
        self.UsePointMaps = UsePointMaps
        self.board = None 

    # agents.py wrapper
    def get_best_move(self, board):
        return self.Start(board)

    def Start(self, board):
        self.board = board
        bestMove = None
        bestScore = -9999
        
        # check if the player is maximizer
        isMaximizer = (self.board.turn == 'w')
        
        if not isMaximizer:
            bestScore = 9999

        # get All the possible move in the current Position
        possibleMoves = self.OrderMoves(self.board.get_valid_moves())

        for move in possibleMoves:
            self.board.apply_move(move)
            
            score = self.minimax(self.depth - 1, not isMaximizer, -10000, 10000)

            if isMaximizer:
                if move.promotion:
                    score += 80
            else:
                if move.promotion:
                    score -= 80
            
            self.board.undo_move()

            if isMaximizer:
                if score >= bestScore:
                    bestScore = score
                    bestMove = move
            else:
                if score <= bestScore:
                    bestScore = score
                    bestMove = move
        
        # print(f"AI Move: {bestMove} | Score: {bestScore}")
        return bestMove

    def minimax(self, depth, isMaximizer, alpha, beta):
        if depth == 0:
            return self.Evaluate()

        valid_moves = self.board.get_valid_moves()

        if not valid_moves:
            if self.board.is_in_check(self.board.turn):
                return -9999 if isMaximizer else 9999
            return 0

        # Sắp xếp nước đi
        valid_moves = self.OrderMoves(valid_moves)

        if isMaximizer:
            bestScore = -9999
            for move in valid_moves:
                self.board.apply_move(move)
                score = self.minimax(depth - 1, False, alpha, beta)
                self.board.undo_move()
                
                bestScore = max(bestScore, score)
                
                if self.AlphaBetaPruning:
                    alpha = max(alpha, bestScore)
                    if beta <= alpha:
                        return bestScore
            return bestScore
        else:
            bestScore = 9999
            for move in valid_moves:
                self.board.apply_move(move)
                score = self.minimax(depth - 1, True, alpha, beta)
                self.board.undo_move()
                
                bestScore = min(bestScore, score)
                
                # Logic AlphaBeta
                if self.AlphaBetaPruning:
                    beta = min(beta, bestScore)
                    if beta <= alpha:
                        return bestScore
            return bestScore

    def Evaluate(self):
        totalScore = 0
        
        for r in range(8):
            for c in range(8):
                piece = self.board.board[r][c]
                if piece == '.':
                    continue
                
                score = PIECE_VALUES.get(piece, 0) #Base value
                
                # PointMap 
                if self.UsePointMaps:
                    # Lấy map tương ứng
                    p_type_idx = MAP_INDEX.get(piece, 0)
                    position_map = map_points[p_type_idx]
                    
                    if piece.isupper(): # Trắng
                        score += position_map[r][c]
                    else: # Đen
                        flipped_map = np.flipud(position_map) * -1
                        score += flipped_map[r][c]
                
                totalScore += score
                
        return totalScore

    def OrderMoves(self, moves):
        def score_move(move):
            score = 0
            if move.captured:
                victim = PIECE_VALUES.get(move.captured.upper(), 0)
                attacker = PIECE_VALUES.get(move.piece.upper(), 0)
                score += 10 * victim - attacker
            if move.promotion:
                score += 900
            return score
            
        moves.sort(key=score_move, reverse=True)
        return moves