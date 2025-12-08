import os
import json
import torch
import chess
import random
import torch.nn as nn
from tqdm.auto import tqdm
from typing import List, Dict, Tuple, Set
from huggingface_hub import PyTorchModelHubMixin

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


################################################################################
# MAPPING

# --- Constants --- #
MAX_HALFMOVES = 128 # cap for embedding table size
MAX_FULLMOVES = 256 # cap for embedding table size

# --- Helper Mappings --- #
PIECE_TO_IDX: Dict[str, int] = {
    'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,
    'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11,
    '.': 12
}
IDX_TO_PIECE: Dict[int, str] = {v: k for k, v in PIECE_TO_IDX.items()}
EMPTY_SQ_IDX = PIECE_TO_IDX['.']
# Map algebraic square notation (e.g., 'a1', 'h8') to 0-63 index
# a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
SQUARE_TO_IDX: Dict[str, int] = {
    f"{file}{rank}": (rank - 1) * 8 + (ord(file) - ord('a'))
    for rank in range(1, 9)
    for file in 'abcdefgh'
}
IDX_TO_SQUARE: Dict[int, str] = {v: k for k, v in SQUARE_TO_IDX.items()}



# --- Coordinate and Notation Helpers ---

# Precompute maps for efficiency
_IDX_TO_COORDS: Dict[int, Tuple[int, int]] = {i: (i // 8, i % 8) for i in range(64)} # (rank, file) 0-7
_COORDS_TO_IDX: Dict[Tuple[int, int], int] = {v: k for k, v in _IDX_TO_COORDS.items()}
_IDX_TO_ALG: Dict[int, str] = {
    i: f"{chr(ord('a') + file)}{rank + 1}"
    for i, (rank, file) in _IDX_TO_COORDS.items()
}
_ALG_TO_IDX: Dict[str, int] = {v: k for k, v in _IDX_TO_ALG.items()}

def _coords_to_alg(r: int, f: int) -> str:
    """Converts 0-indexed (rank, file) to algebraic notation."""
    if 0 <= r < 8 and 0 <= f < 8:
        return f"{chr(ord('a') + f)}{r + 1}"
    # This should not happen with valid indices, but good for safety
    raise ValueError(f"Invalid coordinates: ({r}, {f})")

def generate_structurally_valid_move_map() -> Dict[str, int]:
    """
    Generates a dictionary mapping chess moves that are geometrically possible
    by *some* standard piece (K, Q, R, B, N, or P) to unique integer indices.
    It excludes moves that are structurally impossible for any piece to make
    in one turn (e.g., a1->h5 for non-knight).
    Includes standard UCI promotions (e.g., "e7e8q"), replacing the
    corresponding simple pawn move to the final rank (e.g., "e7e8").
    This is based purely on piece movement geometry, not the current board state.
    Returns:
        Dict[str, int]: A map from the valid UCI move string to a unique
                        integer index (0 to N-1). The size N is expected
                        to be around 1800-1900.
    """
    valid_moves: Set[str] = set()
    # Keep track of base moves (like 'e7e8') that are replaced by promotions
    # according to UCI standard.
    promo_base_moves_to_exclude: Set[str] = set()

    # 1. Generate all geometrically possible non-promotion moves
    for from_idx in range(64):
        from_r, from_f = _IDX_TO_COORDS[from_idx]
        from_alg = _IDX_TO_ALG[from_idx]

        for to_idx in range(64):
            if from_idx == to_idx:
                continue

            to_r, to_f = _IDX_TO_COORDS[to_idx]
            to_alg = _IDX_TO_ALG[to_idx]
            dr, df = to_r - from_r, to_f - from_f
            abs_dr, abs_df = abs(dr), abs(df)

            # Check if the geometry matches any standard piece movement
            # Note: Queen moves are covered by Rook + Bishop checks.
            # Note: Pawn single pushes/captures are covered by King/Rook/Bishop geometry.
            # Note: Pawn double pushes are covered by Rook geometry.
            is_king_move = max(abs_dr, abs_df) == 1
            is_knight_move = (abs_dr == 2 and abs_df == 1) or (abs_dr == 1 and abs_df == 2)
            is_rook_move = dr == 0 or df == 0 # Includes King horiz/vert & pawn double push
            is_bishop_move = abs_dr == abs_df # Includes King diagonal & pawn capture/push

            if is_king_move or is_knight_move or is_rook_move or is_bishop_move:
                 uci_move = f"{from_alg}{to_alg}"
                 valid_moves.add(uci_move)


    # 2. Generate promotion moves explicitly and mark base moves for exclusion
    promo_pieces = ['q', 'r', 'b', 'n']
    for from_f in range(8):
        # White promotions (from rank 7 (idx 6) to rank 8 (idx 7))
        from_r_w, to_r_w = 6, 7
        if from_r_w != 7: # Ensure we are on the correct rank before promotion
            from_alg_w = _coords_to_alg(from_r_w, from_f)
            # Possible destinations: push (df=0), capture left (df=-1), capture right (df=1)
            for df in [-1, 0, 1]:
                to_f_w = from_f + df
                if 0 <= to_f_w < 8:
                    to_alg_w = _coords_to_alg(to_r_w, to_f_w)
                    base_move = f"{from_alg_w}{to_alg_w}"
                    #promo_base_moves_to_exclude.add(base_move) # Mark e.g. "e7e8" for exclusion
                    for p in promo_pieces:
                        valid_moves.add(f"{base_move}{p}") # Add e.g. "e7e8q"

        # Black promotions (from rank 2 (idx 1) to rank 1 (idx 0))
        from_r_b, to_r_b = 1, 0
        if from_r_b != 0: # Ensure we are on the correct rank before promotion
            from_alg_b = _coords_to_alg(from_r_b, from_f)
            # Possible destinations: push (df=0), capture left (df=-1), capture right (df=1)
            for df in [-1, 0, 1]:
                to_f_b = from_f + df
                if 0 <= to_f_b < 8:
                    to_alg_b = _coords_to_alg(to_r_b, to_f_b)
                    base_move = f"{from_alg_b}{to_alg_b}"
                    #promo_base_moves_to_exclude.add(base_move) # Mark e.g. "e2e1" for exclusion
                    for p in promo_pieces:
                        valid_moves.add(f"{base_move}{p}") # Add e.g. "e2e1q"

    # 3. Remove the base moves that were replaced by promotions
    final_valid_moves = valid_moves - promo_base_moves_to_exclude

    # 4. Add draw claim
    final_valid_moves.add("<claim_draw>")

    # 5. Create the final map with sorted keys for deterministic indices
    sorted_moves = sorted(list(final_valid_moves))
    move_map = {move: i for i, move in enumerate(sorted_moves)}

    # Optional: Print the number of moves found for verification
    # print(f"Generated {len(move_map)} structurally valid unique UCI moves.")

    return move_map


UCI_MOVE_TO_IDX = generate_structurally_valid_move_map()
IDX_TO_UCI_MOVE = {v:k for k,v in UCI_MOVE_TO_IDX.items()}


################################################################################
# ChessFormer


# --- Tokenizer --- #
class FENTokenizer(nn.Module):
    """Convert FEN (and repetitions) to a sequence of tokens"""
    def __init__(self, hidden_size,dtype):
        super().__init__()

        self.side_embed = nn.Embedding(2,hidden_size,dtype=dtype) # black/white embedding

        self.castling_embed_k = nn.Parameter(torch.randn(1,1,hidden_size,dtype=dtype))
        self.castling_embed_q = nn.Parameter(torch.randn(1,1,hidden_size,dtype=dtype))
        self.castling_embed_K = nn.Parameter(torch.randn(1,1,hidden_size,dtype=dtype))
        self.castling_embed_Q = nn.Parameter(torch.randn(1,1,hidden_size,dtype=dtype))
        self.no_castling_embed = nn.Parameter(torch.randn(1,1,hidden_size,dtype=dtype))

        self.piece_embed = nn.Embedding(13,hidden_size,dtype=dtype) # 6 for white pieces, 6 for black pieces, 1 for empty

        self.no_en_passant_embed = nn.Parameter(torch.randn(1,1,hidden_size,dtype=dtype)) # use positional embed for the target square, or a special one for '-'

        self.half_move_embed = nn.Embedding(MAX_HALFMOVES,hidden_size,dtype=dtype)

        self.full_move_embed = nn.Embedding(MAX_FULLMOVES,hidden_size,dtype=dtype)

        self.repetition_embed = nn.Embedding(3,hidden_size,dtype=dtype)
        
        self.pos_embed = nn.Embedding(64,hidden_size,dtype=dtype) # positional embedding

    def _parse_fen_string(self, fen_str: str) -> Dict:
        parts = fen_str.split()
        if len(parts) != 6:
            raise ValueError(f"Invalid FEN string: {fen_str}. Expected 6 fields")
        return {
            "piece_placement": parts[0],
            "side_to_move": parts[1],
            "castling": parts[2],
            "en_passant": parts[3],
            "halfmove_clock": parts[4],
            "fullmove_number": parts[5],
        }

    def forward(self, fen_list: List[str], repetitions: torch.Tensor) -> torch.Tensor:
        """
        Args:
            fen: List of fen strings
        
        Returns:
            torch tensor of shape (n_fen,73,hidden_size) where 73 tokens consists of:
                64 piece tokens (fen's first field) +
                1 which-side-to-move token (fen's second field) +
                4 casting rights tokens (fen's third field) + 
                1 en-passant target token (fen's fourth field) + 
                1 half move clock token (fen's fifth field) +
                1 full move number token (fen's fifth field) +
                1 repetition count token (repetitions input)
        """
        batch_size = len(fen_list)
        assert batch_size == repetitions.shape[0]
        assert len(repetitions.size()) == 1
        batch_tokens = []
        device = self.side_embed.weight.device

        # Precompute all square indices
        square_indices = torch.arange(64, device=device)
        all_pos_embeds = self.pos_embed(square_indices) # (64,D)

        for fen_str in fen_list:
            parsed_fen = self._parse_fen_string(fen_str)
            tokens = []

            # --- 1. Piece Placement (64 tokens) ---
            piece_indices = torch.full((64,), EMPTY_SQ_IDX, dtype=torch.long, device=device)
            current_rank = 7 # Start from rank 8
            current_file = 0 # Start from file 'a'
            for char in parsed_fen["piece_placement"]:
                if char == '/':
                    current_rank -= 1
                    current_file = 0
                elif char.isdigit():
                    current_file += int(char)
                elif char in PIECE_TO_IDX:
                    sq_idx = current_rank * 8 + current_file
                    if 0 <= sq_idx < 64:
                         piece_indices[sq_idx] = PIECE_TO_IDX[char]
                    else:
                         raise ValueError(f"Invalid FEN piece placement: {parsed_fen['piece_placement']}")
                    current_file += 1
                else:
                     raise ValueError(f"Invalid character in FEN piece placement: {char}")

            piece_embeds = self.piece_embed(piece_indices) # (64, D)
            # Add positional embeddings
            board_tokens = piece_embeds + all_pos_embeds # (64, D)
            tokens.append(board_tokens)

            # --- 2. Side to Move (1 token) ---
            side_idx = 0 if parsed_fen["side_to_move"] == 'w' else 1
            side_token = self.side_embed(torch.tensor(side_idx, device=device)).unsqueeze(0) # (1, D)
            tokens.append(side_token)

            # --- 3. Castling Rights (4 tokens) ---
            castling_str = parsed_fen["castling"]
            castling_tokens = torch.cat([
                self.castling_embed_K if 'K' in castling_str else self.no_castling_embed.expand(1, 1, -1),
                self.castling_embed_Q if 'Q' in castling_str else self.no_castling_embed.expand(1, 1, -1),
                self.castling_embed_k if 'k' in castling_str else self.no_castling_embed.expand(1, 1, -1),
                self.castling_embed_q if 'q' in castling_str else self.no_castling_embed.expand(1, 1, -1)
            ], dim=1).squeeze(0) # (4, D)
            tokens.append(castling_tokens)

            # --- 4. En Passant Target (1 token) ---
            en_passant_str = parsed_fen["en_passant"]
            if en_passant_str == '-':
                en_passant_token = self.no_en_passant_embed.squeeze(0) # (1, D)
            else:
                if en_passant_str in SQUARE_TO_IDX:
                    sq_idx = SQUARE_TO_IDX[en_passant_str]
                    en_passant_token = self.pos_embed(torch.tensor(sq_idx, device=device)).unsqueeze(0) # (1, D)
                else:
                    raise ValueError(f"Invalid en passant square: {en_passant_str}")
            tokens.append(en_passant_token)

            # --- 5. Half Move Clock (1 token) ---
            try:
                half_move_int = int(parsed_fen["halfmove_clock"])
            except ValueError:
                 raise ValueError(f"Invalid halfmove clock value: {parsed_fen['halfmove_clock']}")
            # Clamp value before embedding lookup
            half_move_clamped = torch.clamp(torch.tensor(half_move_int, device=device), 0, MAX_HALFMOVES - 1)
            half_move_token = self.half_move_embed(half_move_clamped).unsqueeze(0) # (1, D)
            tokens.append(half_move_token)

            # --- 6. Full Move Number (1 token) ---
            try:
                full_move_int = int(parsed_fen["fullmove_number"])
            except ValueError:
                 raise ValueError(f"Invalid fullmove number value: {parsed_fen['fullmove_number']}")
             # Clamp value (min 1 for full moves) before embedding lookup (adjusting for 0-based index)
            full_move_clamped = torch.clamp(torch.tensor(full_move_int, device=device), 1, MAX_FULLMOVES) - 1
            full_move_token = self.full_move_embed(full_move_clamped).unsqueeze(0) # (1, D)
            tokens.append(full_move_token)

            # Concatenate all tokens for this FEN string
            # Shapes: (64, D), (1, D), (4, D), (1, D), (1, D), (1, D) -> Total 72 tokens
            fen_embedding = torch.cat(tokens, dim=0) # (72, D)
            batch_tokens.append(fen_embedding)

        # Stack into a batch
        batch_tokens = torch.stack(batch_tokens, dim=0) # (B,72,D)

        # ---7. Repetition Count (1 token) ---
        repetitions = repetitions - 1 # from 1~3 to 0~2
        repetitions = torch.clamp(repetitions,0,2) # if repetition count >3 but no player claimed a draw, it will be treated as 3 repetitions
        repetition_tokens = self.repetition_embed(repetitions) # (B,D)
        repetition_tokens = repetition_tokens.unsqueeze(1) # (B,1,D)

        return torch.cat([batch_tokens,repetition_tokens], dim=1) # (B, 73, D)

# --- Helper Modules --- #
class SwiGLUFFN(nn.Module):
    def __init__(self,
                 d_model, 
                 dim_feedforward,
                 dropout: float,
                 bias_up: bool=False,
                 bias_gate: bool=False,
                 bias_down: bool=True,
                 dtype=None):
        super().__init__()
        self.up_proj = nn.Linear(d_model,dim_feedforward,bias=bias_up,dtype=dtype)
        self.gate_proj = nn.Linear(d_model,dim_feedforward,bias=bias_gate,dtype=dtype)
        self.down_proj = nn.Linear(dim_feedforward,d_model,bias=bias_down,dtype=dtype)

        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.up_proj(x) * self.dropout(nn.functional.silu(self.gate_proj(x)))
        return self.down_proj(x)

class TransformerEncoderLayer(nn.Module):
    """Custom transformer encoder layer with RMSNorm and SwiGLUFFN"""
    def __init__(self,
                 d_model: int,
                 nhead: int,
                 dim_feedforward: int,
                 dropout: float,
                 batch_first: bool=True,
                 norm_first: bool=False,
                 dtype=None):
        super().__init__()
        self.norm_first = norm_first

        self.norm1 = nn.RMSNorm(d_model,dtype=dtype)
        self.dropout_sa = nn.Dropout(dropout)
        self.self_attn = nn.MultiheadAttention(
            d_model,
            nhead,
            dropout=dropout,
            bias=False,
            batch_first=batch_first,
            dtype=dtype
        )

        self.norm2 = nn.RMSNorm(d_model,dtype=dtype)
        self.dropout_ff = nn.Dropout(dropout)
        self.mlp = SwiGLUFFN(
            d_model,
            dim_feedforward,
            dropout=dropout,
            bias_up=False,
            bias_gate=False,
            bias_down=True,
            dtype=dtype
            )

    def forward(self, x, return_attention=False):
        if self.norm_first:
            if return_attention:
                x_norm = self.norm1(x)
                attn_output, attn_weights = self._sa_block(x_norm,return_attention=True)
                x = x + attn_output
                x = x + self._ff_block(self.norm2(x))
                return x, attn_weights
            else:
                x = x + self._sa_block(self.norm1(x))
                x = x + self._ff_block(self.norm2(x))
                return x
        else:
            if return_attention:
                attn_output, attn_weights = self._sa_block(x, return_attention=True)
                x = self.norm1(x + attn_output)
                x = self.norm2(x + self._ff_block(x))
                return x, attn_weights
            else:
                x = self.norm1(x + self._sa_block(x))
                x = self.norm2(x + self._ff_block(x))
                return x
    
    def _sa_block(self, x, return_attention=False):
        if return_attention:
            attn_output, attn_weights = self.self_attn(x,x,x,need_weights=True,average_attn_weights=False)
            return self.dropout_sa(attn_output), attn_weights
        else:
            x = self.self_attn(x,x,x)[0]
            return self.dropout_sa(x)
    
    def _ff_block(self,x):
        x = self.mlp(x)
        return self.dropout_ff(x)
    nn.TransformerEncoderLayer

# --- Model Arch --- #
class ChessFormerModel(nn.Module, PyTorchModelHubMixin):
    def __init__(self,
                 num_blocks,
                 hidden_size,
                 intermediate_size,
                 num_heads,
                 dropout: float=0.00,
                 possible_moves: int=len(IDX_TO_UCI_MOVE), # 1969 structurally valid moves
                 dtype=None):
        super().__init__()
        self.fen_tokenizer = FENTokenizer(hidden_size,dtype=dtype)

        self.act_token = nn.Parameter(torch.randn((1,1,hidden_size),dtype=dtype) * 0.02)
        self.val_token = nn.Parameter(torch.randn((1,1,hidden_size),dtype=dtype) * 0.02)

        self.act_proj = nn.Linear(hidden_size,possible_moves,dtype=dtype)
        self.val_proj = nn.Linear(hidden_size,1,dtype=dtype)

        self.blocks = nn.ModuleList(
            TransformerEncoderLayer(
                d_model=hidden_size,
                nhead=num_heads,
                dim_feedforward=intermediate_size,
                dropout=dropout,
                batch_first=True,
                norm_first=True,
                dtype=dtype               
            ) for _ in range(num_blocks)
        )
        self.dtype=dtype
        self.possible_moves = possible_moves

        self.final_norm = nn.RMSNorm(hidden_size)

        self._initialize_weights()
        
    def _initialize_weights(self):
        """Initialize weights"""
        for m in self.modules():
            if isinstance(m,nn.Linear):
                nn.init.kaiming_normal_(m.weight,mode='fan_in',nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, std=0.02)
            elif isinstance(m, nn.LayerNorm):
                if hasattr(m, 'weight'):
                    nn.init.constant_(m.weight, 1.0)
                if hasattr(m, 'bias') and m.bias is not None:
                    nn.init.constant_(m.weight, 0.0)
            elif isinstance(m, nn.RMSNorm):
                if hasattr(m, 'weight'):
                    nn.init.constant_(m.weight, 1.0)

        tokenizer_params = dict(self.fen_tokenizer.named_parameters())

        params_to_init = [
            self.act_token, self.val_token,
            tokenizer_params.get('castling_embed_k'), tokenizer_params.get('castling_embed_q'),
            tokenizer_params.get('castling_embed_K'), tokenizer_params.get('castling_embed_Q'),
            tokenizer_params.get('no_castling_embed'), tokenizer_params.get('no_en_passant_embed')
        ]

        for param in params_to_init:
            if param is not None and param.requires_grad:
                nn.init.normal_(param, std=0.02)


    def forward(self, fen: List[str], repetitions: torch.Tensor, return_attention: bool=False) -> torch.Tensor:
        x = self.fen_tokenizer(fen,repetitions) # (B,73,D), pos embed are added here
        bs = x.shape[0]
        x = torch.cat([x,self.act_token.expand(bs,-1,-1),self.val_token.expand(bs,-1,-1)],dim=1) # (B,75,D)

        attention_maps = [] if return_attention else None

        for block in self.blocks:
            if return_attention:
                x, attn = block(x, return_attention=True)
                attention_maps.append(attn)
            else:
                x = block(x)

        x = self.final_norm(x)

        act = x[:,-2,:]
        val = x[:,-1,:]
        act_logits = self.act_proj(act) # (B,1969)
        val = self.val_proj(val) # (B,1)

        if return_attention:
            return act_logits, val.squeeze(1), attention_maps
        else:
            return act_logits, val.squeeze(1)

def load_model(ckpt_path):
    checkpoint = torch.load(ckpt_path)
    model_config = checkpoint["model_config"]
    model = ChessFormerModel(**model_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    return model

################################################################################
# Operations

model = ChessFormerModel.from_pretrained("kaupane/ChessFormer-SL", cache_dir="./model_cache")
model.to(device)
model.eval()

def get_random_move(fen: str) -> str:
    board = chess.Board(fen)
    legal_moves = list(board.legal_moves)
    random_move = random.choice(legal_moves)
    return str(random_move)

def get_smart_move(fen: str) -> str:
    fens = [fen]
    reps = torch.tensor([1]).to(device)
    with torch.inference_mode():
        move_logits, pos_value = model(fens, reps)
    move_idx = torch.argmax(move_logits)
    move = IDX_TO_UCI_MOVE[int(move_idx)]

    board = chess.Board(fen)
    if chess.Move.from_uci(move) not in board.legal_moves:
        return get_random_move(fen)
    return move

def play_match(white_agent, black_agent, max_moves=200):
    board = chess.Board()
    moves_count = 0
    
    while not board.is_game_over() and moves_count < max_moves:
        fen = board.fen()
        
        try:
            if board.turn == chess.WHITE:
                move_str = white_agent(fen)
            else:
                move_str = black_agent(fen)
                
            move = chess.Move.from_uci(move_str)
            
            if move in board.legal_moves:
                board.push(move)
            else:
                # If an agent makes an illegal move, they instantly lose
                print(f"Illegal move by {'White' if board.turn == chess.WHITE else 'Black'}: {move_str}")
                return 0.0 if board.turn == chess.WHITE else 1.0
                
        except Exception as e:
            # If an agent crashes, they lose
            return 0.0 if board.turn == chess.WHITE else 1.0
            
        moves_count += 1

    result = board.result()
    
    if result == '1-0':
        return 1.0
    elif result == '0-1':
        return 0.0
    elif result == '1/2-1/2':
        return 0.5
    else:
        # Game hit max_moves without a clear result -> Treat as Draw
        return 0.5

def evaluate_agents(smart_agent, random_agent, num_games=100):
    """
    Plays num_games between smart_agent and random_agent.
    Swaps colors halfway through.
    """
    if num_games % 2 != 0:
        print("Warning: num_games should be even to ensure equal color distribution. Adding 1 game.")
        num_games += 1

    smart_wins = 0
    random_wins = 0
    draws = 0
    
    print(f"Starting evaluation: {num_games} games...")
    
    for i in tqdm(range(num_games)):
        # First half: Smart Agent plays WHITE
        if i < num_games // 2:
            score = play_match(white_agent=smart_agent, black_agent=random_agent)
            if score == 1.0:
                smart_wins += 1
            elif score == 0.0:
                random_wins += 1
            else:
                draws += 1
                
        # Second half: Smart Agent plays BLACK
        else:
            score = play_match(white_agent=random_agent, black_agent=smart_agent)
            # Note: score is 1.0 if White (Random) wins, 0.0 if Black (Smart) wins
            if score == 1.0:
                random_wins += 1
            elif score == 0.0:
                smart_wins += 1
            else:
                draws += 1

    # --- Statistics ---
    win_rate = (smart_wins / num_games) * 100
    non_loss_rate = ((smart_wins + draws) / num_games) * 100
    
    print("\n" + "="*30)
    print(f"EVALUATION RESULTS ({num_games} Games)")
    print("="*30)
    print(f"Smart Agent Wins: {smart_wins}")
    print(f"Random Agent Wins: {random_wins}")
    print(f"Draws:            {draws}")
    print("-" * 30)
    print(f"Smart Agent Win Rate:      {win_rate:.2f}%")
    print(f"Smart Agent Non-Loss Rate: {non_loss_rate:.2f}%")

    results = {
        "num_games": num_games,
        "smart_wins": smart_wins,
        "random_wins": random_wins,
        "draws": draws,
        "win_rate": win_rate,
        "non_loss_rate": non_loss_rate,
    }

    os.makedirs("output", exist_ok=True)
    with open("output/ml-results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    evaluate_agents(get_smart_move, get_random_move, num_games=100)