import torch
import torch.nn as nn
import torch.nn.functional as F

from .constants import HALFKP_DIM, POLICY_SIZE


class ClippedReLU(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.clamp(x, 0.0, 1.0)


class NNUE(nn.Module):
    """HalfKP-256-32-32-1 NNUE value evaluation network.
    
    Predicts position evaluation in [-1.0, 1.0] from the perspective
    of the side to move (the player whose turn it is).
    - fc1: sparse linear projection (no bias) with ClippedReLU [0, 1]
    - fc2: linear (hidden -> 32) with ClippedReLU [0, 1]
    - fc3: linear (32 -> 32) with ClippedReLU [0, 1]
    - fc_out: linear (32 -> 1) with tanh activation bounded in [-1, 1]
    """

    def __init__(self, halfkp_dim: int = HALFKP_DIM, hidden: int = 256):
        super().__init__()
        self.fc1 = nn.Linear(halfkp_dim, hidden, bias=False)
        self.crelu1 = ClippedReLU()
        self.fc2 = nn.Linear(hidden, 32, bias=True)
        self.crelu2 = ClippedReLU()
        self.fc3 = nn.Linear(32, 32, bias=True)
        self.crelu3 = ClippedReLU()
        self.fc_out = nn.Linear(32, 1, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.crelu1(self.fc1(x))
        x = self.crelu2(self.fc2(x))
        x = self.crelu3(self.fc3(x))
        x = torch.tanh(self.fc_out(x))
        return x.squeeze(-1)


# ModernNNUE alias for 100% backward compatibility with training notebooks and checkpoints
ModernNNUE = NNUE


class PolicyHead(nn.Module):
    """Spatially aware AlphaZero-style CNN policy network.
    
    Operates on an 18-plane 8x8 board representation:
    - Conv stem: 3x3 conv (18 -> filters) + BatchNorm + ReLU
    - Residual tower: res_blocks of [Conv 3x3 -> BN -> ReLU -> Conv 3x3 -> BN] + skip
    - Policy head: 1x1 conv (filters -> 32) + BN + ReLU -> Flatten -> Linear -> num_moves
    """

    def __init__(self, in_planes: int = 18, num_moves: int = POLICY_SIZE, filters: int = 128, res_blocks: int = 6):
        super().__init__()
        self.conv_stem = nn.Sequential(
            nn.Conv2d(in_planes, filters, 3, padding=1),
            nn.BatchNorm2d(filters),
            nn.ReLU(),
        )
        self.res_blocks = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv2d(filters, filters, 3, padding=1),
                    nn.BatchNorm2d(filters),
                    nn.ReLU(),
                    nn.Conv2d(filters, filters, 3, padding=1),
                    nn.BatchNorm2d(filters),
                )
                for _ in range(res_blocks)
            ]
        )
        self.policy_conv = nn.Conv2d(filters, 32, 1)
        self.policy_bn = nn.BatchNorm2d(32)
        self.policy_fc = nn.Linear(32 * 8 * 8, num_moves)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv_stem(x)
        for block in self.res_blocks:
            residual = x
            x = F.relu(block(x) + residual)
        x = F.relu(self.policy_bn(self.policy_conv(x)))
        x = x.view(x.size(0), -1)
        return self.policy_fc(x)