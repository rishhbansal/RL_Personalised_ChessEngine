# RL Personalized Chess Engine & AI Coach ♟️🤖

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C.svg?logo=pytorch)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0-646CFF.svg?logo=vite)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced, hybrid Chess AI and Interactive Coaching Platform combining a **ModernNNUE HalfKP Evaluation Network**, an **AlphaZero-inspired 6-ResBlock Convolutional Policy Head**, **PUCT Monte Carlo Tree Search (MCTS)**, and a **Full-Stack Web Interface** with real-time LLM-driven grandmaster commentary.

The engine learns board evaluation and tactical move intuition through streaming imitation of 20,000,000+ Stockfish-annotated positions, refines decision-making through MCTS self-play reinforcement learning, and delivers an adaptive human-vs-AI sparring experience.

---

## 📑 Table of Contents

- [Key Highlights](#-key-highlights)
- [System Architecture](#-system-architecture)
  - [1. Dual-Head Neural Core](#1-dual-head-neural-core)
  - [2. Monte Carlo Tree Search (PUCT)](#2-monte-carlo-tree-search-puct)
  - [3. Memory-Lean Training Pipeline](#3-memory-lean-training-pipeline)
  - [4. Full-Stack Web App & LLM Coach](#4-full-stack-web-app--llm-coach)
- [Repository Structure](#-repository-structure)
- [Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [1. Backend Setup](#1-backend-setup-fastapi--neural-engine)
  - [2. Frontend Setup](#2-frontend-setup-react--vite)
- [Engine Benchmarks & Performance](#-engine-benchmarks--performance)
- [Features & Capabilities](#-features--capabilities)
- [Deployment](#-deployment)
- [Credits & Academic Affiliation](#-credits--academic-affiliation)

---

## 🌟 Key Highlights

- **ModernNNUE Value Network**: Features a 41,040-dimensional HalfKP sparse accumulator with $O(1)$ incremental delta updates during tree search, computing centipawn evaluations at blazing speed.
- **Deep Spatial Policy Head**: An 18-plane board representation passed through a 6-residual-block convolutional network projecting to 4,672 discrete chess move classes, masked by legal move filters.
- **AlphaZero PUCT Search**: Monte Carlo Tree Search executing up to 800 simulations per move, using Dirichlet noise at root for robust exploration and temperature-controlled move selection.
- **In-Memory Streaming Dataset (Zero Disk Extraction)**: Streams directly from 22.4 GB compressed `lichess_db_eval.jsonl.zst` files into lightweight Python primitives, avoiding RAM OOM and bypassing hundreds of gigabytes of disk decompression.
- **Interactive Full-Stack Web Platform**: Responsive chessboard UI with live evaluation bar, candidate move arrows, adaptive personality sliders (Aggression, Risk Tolerance, Difficulty, Tactical Lean), and match history.
- **Autonomous Fallback Database**: Seamless local JSON database persistence (`backend/data/local_db.json`) ensuring game records and player profiles persist reliably even without an external MongoDB daemon.
- **LLM Chess Coach**: Integrated Groq / OpenRouter AI analysis explaining the strategic rationale behind moves, blunders, and evaluation swings.

---

## 🧠 System Architecture

```
                                  ┌────────────────────────────────────────┐
                                  │      Lichess 20M+ Evaluations          │
                                  │       (Compressed .zst Stream)         │
                                  └──────────────────┬─────────────────────┘
                                                     │
                                                     ▼
                                  ┌────────────────────────────────────────┐
                                  │       Supervised Pre-Training          │
                                  │  - Value Head: MSE vs Centipawn/WDL   │
                                  │  - Policy Head: Cross-Entropy Softmax  │
                                  └──────────────────┬─────────────────────┘
                                                     │
                                                     ▼
                                  ┌────────────────────────────────────────┐
                                  │        MCTS Self-Play (RL)             │
                                  │  - 800 PUCT Sims with Dirichlet Noise  │
                                  │  - Experience Replay & Distillation    │
                                  └──────────────────┬─────────────────────┘
                                                     │
                             ┌───────────────────────┴───────────────────────┐
                             ▼                                               ▼
             ┌───────────────────────────────┐               ┌───────────────────────────────┐
             │       ModernNNUE Value        │               │       Spatial Policy Head     │
             │   - HalfKP (41,040 inputs)    │               │   - 18 planes (8x8)           │
             │   - 2x256 -> 32 -> 32 -> 1    │               │   - 6 ResBlocks (128 filters) │
             │   - O(1) Accumulator Deltas   │               │   - 4,672 action logits       │
             └───────────────┬───────────────┘               └───────────────┬───────────────┘
                             │                                               │
                             └───────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │   PUCT Search Action Select │
                                      └──────────────┬──────────────┘
                                                     │
                      ┌──────────────────────────────┴──────────────────────────────┐
                      ▼                                                             ▼
       ┌──────────────────────────────┐                              ┌──────────────────────────────┐
       │   UCI Engine Protocol        │                              │   FastAPI Web API Backend    │
       │   (Arena / CuteChess / CLI)  │                              │   - Async MCTS Inference     │
       └──────────────────────────────┘                              │   - OpenRouter / Groq LLM    │
                                                                     │   - Local/Mongo Persistence  │
                                                                     └──────────────┬───────────────┘
                                                                                    │ REST / JSON
                                                                                    ▼
                                                                     ┌──────────────────────────────┐
                                                                     │   React 18 + Vite Frontend   │
                                                                     │   - Live Eval Bar & Arrows   │
                                                                     │   - Personality Sliders      │
                                                                     │   - Match History & Review   │
                                                                     └──────────────────────────────┘
```

### 1. Dual-Head Neural Core
- **HalfKP Accumulator**: Maps sparse piece positions relative to each king's square (`64 squares × 10 piece types × 64 squares = 40,960` features per perspective). Rather than evaluating from scratch each ply, `push()` updates only changed squares via delta addition/subtraction.
- **Evaluation MLP**: Accumulators are clamped via clipped activations and passed through dense layers to output a normalized scalar evaluation:
  $$v = \tanh\left(\frac{\text{cp}_{\text{mover}}}{400.0}\right) \in [-1.0, 1.0]$$
- **Spatial CNN Policy Head**: Encodes the board into 18 binary planes (piece positions, castling rights, en passant, active color), processes them through a convolutional stem and 6 Residual Blocks with skip connections, and projects to 4,672 move probabilities with legal-move masking.

### 2. Monte Carlo Tree Search (PUCT)
Each search iteration evaluates candidate trajectories by maximizing the Upper Confidence Bound for Trees:
$$a^* = \arg\max_a \left[ Q(s, a) + c_{\text{puct}} \cdot P(s, a) \cdot \frac{\sqrt{\sum_b N(s, b)}}{1 + N(s, a)} \right]$$
- Evaluates leaf nodes using the joint neural heads.
- Backpropagates perspective-flipped values along visited branches.
- Introduces Dirichlet noise $\text{Dir}(\alpha=0.3)$ at the root during training to encourage diverse tactical exploration.

### 3. Memory-Lean Training Pipeline
Traditional chess training pipelines load massive uncompressed datasets into memory, leading to RAM crashes. Our architecture implements:
- **Zero-Disk Extraction**: Reads `lichess_db_eval.jsonl.zst` in-memory via Python `zstandard` streams.
- **Primitive Buffering**: Stores lightweight tuples `(fen, val, move_indices, move_probs)` (~120 bytes/sample) in RAM instead of allocating heavyweight tensors up-front.
- **On-The-Fly Batch Assembly**: Transforms primitives into PyTorch CUDA tensors strictly inside the DataLoader `collate_fn`.

### 4. Full-Stack Web App & LLM Coach
- **FastAPI Core**: Serves AI move predictions, depth analysis, and game validation asynchronously.
- **Dual Storage Engine**: Automatically connects to MongoDB if available, or seamlessly persists user profiles and game histories to an autonomous atomic local JSON database (`backend/data/local_db.json`).
- **Personalized Sliders**: Dynamically blends the AI's search depth, evaluation heuristics, and move noise according to user-customized traits (Difficulty, Aggression, Risk Tolerance, Tactical Lean).
- **LLM Coach Integration**: Formulates structured board contexts (FEN before/after, top alternatives, evaluation delta) and queries Groq/OpenRouter models to explain tactical ideas in natural, educational English.

---

## 📁 Repository Structure

```text
RL_Personalised_ChessEngine/
├── backend/
│   ├── app.py                     # FastAPI application endpoints & engine bridge
│   ├── database.py                # Hybrid MongoDB + Local JSON persistence layer
│   ├── schemas.py                 # Pydantic data schemas
│   ├── security.py                # JWT authentication & password hashing
│   ├── requirements.txt           # Backend Python dependencies
│   ├── data/                      # Persistent local storage (local_db.json)
│   └── engine/
│       ├── model.py               # ModernNNUE & 6-ResBlock Policy Head architectures
│       ├── mcts.py                # Incremental PUCT Monte Carlo Tree Search
│       └── weights/               # Trained neural checkpoint weights
│           ├── nnue_distilled(rl).pth
│           └── policy_distilled(rl).pth
├── frontend/
│   ├── src/
│   │   ├── components/            # Chessboard, EvalBar, Sliders, History, Coach dialogs
│   │   ├── pages/                 # Play, Analysis, Profile, Login/Register pages
│   │   └── services/              # API client & game state stores
│   ├── package.json               # Frontend dependencies (React, Vite, Tailwind/Lucide)
│   └── vite.config.ts             # Vite build configuration
├── UCI and Engine implementation/
│   ├── Chess_rl.ipynb             # End-to-end training, streaming dataset & RL notebook
│   ├── nnue_distilled(rl).pth     # Exported value weights
│   └── policy_distilled(rl).pth   # Exported policy weights
├── TRAINING_GUIDE.md              # Detailed GPU & streaming training documentation
├── DEPLOYMENT_GUIDE.md            # Free deployment manual (Render + Vercel)
├── Run backend frontend.txt       # Rapid startup command sheet
├── split_zst_dataset.py           # Zstandard dataset chunk splitter
├── stockfish_zst_dataset.py       # High-throughput streaming PyTorch Dataset
├── train_supervised.py            # Supervised pre-training script
├── train_rl.py                    # MCTS self-play reinforcement learning loop
└── play_vs_stockfish.py           # Automated evaluation & ACPL benchmark runner
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & npm
- *(Optional)* NVIDIA GPU with CUDA support for training / fast GPU inference
- *(Optional)* [Stockfish binary](https://stockfishchess.org/download/) if you wish to run automated benchmark games via `play_vs_stockfish.py`

---

### 1. Backend Setup (FastAPI & Neural Engine)

1. Open a terminal and navigate to the `backend` folder:
   ```powershell
   cd RL_Personalised_ChessEngine\backend
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1       # On Windows
   # source venv/bin/activate       # On Linux/macOS
   ```

3. Install required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. *(Optional)* Configure your `.env` file in `backend/`:
   ```env
   JWT_SECRET_KEY=your_super_secret_jwt_key
   OPENROUTER_API_KEY=your_openrouter_or_groq_api_key_here
   ```

5. Launch the backend server:
   ```powershell
   python -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload
   ```
   *The backend will initialize, load the neural weights from `backend/engine/weights/`, and verify local database storage.*

---

### 2. Frontend Setup (React + Vite)

1. Open a **second terminal** and navigate to the `frontend` folder:
   ```powershell
   cd RL_Personalised_ChessEngine\frontend
   ```

2. Install npm packages:
   ```powershell
   npm install
   ```

3. Start the Vite development server:
   ```powershell
   npm run dev
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5173
   ```
   *You can now register an account, customize your opponent's play style, play live games with MCTS neural evaluations, and request strategic coaching advice!*

---

## 📊 Engine Benchmarks & Performance

The engine was evaluated in automated test matches against **Stockfish 18 (Skill Level 15)**:

| Metric | Benchmark Result |
|:---|:---:|
| **Test Match Series** | 10 Tournament Games |
| **Moves Analyzed** | 103 Game Moves |
| **Average Centipawn Loss (ACPL)** | **93.11 cp / move** |
| **Estimated Base Elo** | **~1603 Elo** |
| **Peak Single-Game Performance** | **66.2 ACPL (~2007 Elo)** |
| **MCTS Throughput** | ~800 simulations/sec (Batched GPU) |

> **Note on Learning Trajectory:** The model demonstrates exceptional tactical resilience as Black, with lower blunder rates and strong counter-attacking lines. Reinforcement self-play fine-tuning continues to narrow the opening-theory gap as White.

---

## 🎮 Features & Capabilities

- **Interactive Chessboard**: Smooth piece animations, legal move indicators, premove support, and last-move highlights.
- **Live Evaluation Bar**: Instant visual feedback of position advantage calculated directly from the HalfKP neural value network.
- **Top Move Arrows**: Displays top candidate moves and visual tactical threats on the board.
- **Personality Sliders**:
  - **Difficulty**: Scales MCTS simulation count and tree depth.
  - **Aggression**: Weights capture and forward-attacking heuristics.
  - **Risk Tolerance**: Modulates policy temperature and willingness to enter sharp lines.
  - **Tactical Lean**: Controls king-safety penalty terms and tactical piece activity.
- **Full Match History & Game Viewer**: Review previous matches, step through moves with an interactive board, and inspect stored evaluations.
- **Grandmaster LLM Feedback**: Get plain-English explanations of key mistakes, missed tactics, and positional plans powered by state-of-the-art LLMs.

---

## 🌐 Deployment

Ready to share your chess engine online? Detailed step-by-step instructions for hosting both the frontend (on Vercel) and the backend (on Render / Hugging Face Spaces) for **100% free** are available in [DEPLOYMENT_GUIDE.md](file:///c:/Users/Rishabh/Downloads/SOC_AIML_20-main/RL_Personalised_ChessEngine/DEPLOYMENT_GUIDE.md).

---

## 👥 Credits & Academic Affiliation

- **Institution:** Indian Institute of Technology Indore (IIT Indore)
- **Initiative:** IITISoC 2026 | Domain: AIML (PS 1 AIML Advanced)
- **Founding Project Team:** Rohan, Poorneshwar, Aman Ahmed, Rishabh, Om
- **Reinforcement Learning, Web Platform Architecture & Optimization:** Rishabh

---

*Licensed under the [MIT License](https://opensource.org/licenses/MIT).*
