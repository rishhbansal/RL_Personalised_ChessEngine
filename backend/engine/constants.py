
import torch

POLICY_SIZE = 4672
HALFKP_DIM = 64 * 10 * 64  # 40960

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
