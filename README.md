# Chess Agent

A chess game with multiple AI opponents, featuring both classical Minimax search and a Transformer-based neural network (ChessFormer).

## ChessFormer

This project integrates [ChessFormer-SL](https://huggingface.co/kaupane/ChessFormer-SL), a supervised learning Transformer model trained to predict chess moves. The model takes FEN board positions as input and outputs move probabilities across ~1969 structurally valid UCI moves.

## How to Run

### Prerequisites

Install [uv](https://docs.astral.sh/uv/) - python package manager:
```bash
pip install uv
```

Install dependencies using [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

### Running the Game

Launch the interactive chess GUI:

```bash
uv run python main.py
```

**Game Modes:**
- Player vs Player
- Player vs Minimax AI
- Minimax vs Random
- ML (ChessFormer) vs Random

### Running Model Evaluation

Evaluate the ChessFormer model against a random agent over 1000 games:

```bash
uv run python chessformer.py
```

Results are saved to `output/ml-results.json`.

## Evaluation Results

### ChessFormer

| Metric | Value |
|--------|-------|
| Games Played | 1000 |
| Smart Agent Wins | 943 |
| Random Agent Wins | 0 |
| Draws | 57 |
| **Win Rate** | **94.30%** |
| **Non-Loss Rate** | **100.00%** |

## Institute Information

This project is developed as part of the **Introduction to Artificial Intelligence** course at **Ho Chi Minh City University of Technology (HCMUT)**.

| | |
|---|---|
| **University** | Ho Chi Minh City University of Technology (HCMUT) |
| **Faculty** | Faculty of Computer Science and Engineering |
| **Course** | Nhập môn Trí tuệ Nhân tạo (CO3061) |
| **Instructor** | Vương Bá Thịnh |
| **Semester** | HK251 (2024-2025) |