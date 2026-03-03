#!/usr/bin/env python3
"""
改进的轨迹级预测密度
=====================
问题：CRS-Drop理论预测停止步数只有2.8%信息捕获。
原因：预测模型太粗糙（只用E[Δ]=-1.83和E[k]=2的均值）。

改进：使用更精确的预测模型，考虑：
1. 起始值n的trailing_ones（第一个CRS的长度已知！）
2. 多级预测：先预测第一个CRS周期，然后用统计预测剩余
"""
import numpy as np
import math
from collections import Counter

def v2(n):
    c = 0
    while n % 2 == 0:
        c += 1
        n //= 2
    return c

def T_acc(n):
    m = 3 * n + 1
    while m % 2 == 0:
        m //= 2
    return m

def trailing_ones(n):
    c = 0
    while n & 1:
        c += 1
        n >>= 1
    return c

def entropy(seq):
    c = Counter(seq)
    total = len(seq)
    return -sum((v/total) * np.log2(v/total) for v in c.values() if v > 0)

def mutual_information(x, y):
    hx = entropy(x)
    hy = entropy(y)
    hxy = entropy(list(zip(x, y)))
    return max(0, hx + hy - hxy)

def improved_prediction(n):
    """
    改进的停止步数预测
    
    1. 第一个CRS长度 = trailing_ones(n)，这是精确的
    2. 第一个CRS后的值 ≈ n × (3/2)^k（近似）
    3. 之后的剩余用统计模型
    """
    k1 = trailing_ones(n)
    log_n = math.log2(n)
    
    # 第一个CRS后的log值
    # CRS上升 k1 × log₂(3/2) = k1 × 0.585
    # Drop ≈ 3（期望值）
    log_after_first = log_n + k1 * 0.585 - 3
    
    if log_after_first <= 0:
        return k1 + 1  # 一个周期就收敛
    
    # 剩余周期数 ≈ log_after_first / 1.80（用轨迹采样的1.80而非理论1.83）
    remaining_cycles = log_after_first / 1.80
    
    # 每周期步数 ≈ E[k] + 1 = 3
    remaining_steps = remaining_cycles * 3
    
    return k1 + remaining_steps

def compute_improved_rho(N=100000):
    """计算改进模型的ρ"""
    print("=" * 70)
    print("改进的轨迹预测密度")
    print("=" * 70)
    
    actual_steps = []
    pred_naive = []      # 仅用log₂(n)
    pred_improved = []   # 用trailing_ones + CRS-Drop理论
    pred_trailing = []   # 仅用trailing_ones
    
    for n in range(3, 2*N, 2):
        current = n
        steps = 0
        while current > 1 and steps < 5000:
            current = T_acc(current)
            steps += 1
        if current > 1:
            continue
        
        actual_steps.append(steps)
        log_n = math.log2(n)
        k1 = trailing_ones(n)
        
        # 朴素预测
        pred_naive.append(int(log_n / 1.80 * 3))
        
        # 改进预测
        pred_improved.append(int(improved_prediction(n)))
        
        # 仅trailing_ones
        pred_trailing.append(k1)
    
    # 离散化
    def disc(arr, bins=40):
        arr = np.array(arr, dtype=float)
        pct = np.percentile(arr, np.linspace(0, 100, bins+1))
        pct = np.unique(pct)
        return np.digitize(arr, pct[1:-1])
    
    d_actual = disc(actual_steps)
    d_naive = disc(pred_naive)
    d_improved = disc(pred_improved)
    d_trailing = disc(pred_trailing)
    
    H_actual = entropy(d_actual)
    I_naive = mutual_information(d_naive, d_actual)
    I_improved = mutual_information(d_improved, d_actual)
    I_trailing = mutual_information(d_trailing, d_actual)
    
    print(f"\n样本数: {len(actual_steps)}")
    print(f"H(actual_steps) = {H_actual:.4f} bits")
    print(f"\n{'模型':>20} | {'I(pred;actual)':>14} | {'捕获率':>8} | {'RMSE':>8}")
    print("-" * 60)
    
    for name, pred, I_val in [
        ("log₂(n)仅", pred_naive, I_naive),
        ("trailing_ones仅", pred_trailing, I_trailing),
        ("改进CRS-Drop", pred_improved, I_improved),
    ]:
        rmse = np.sqrt(np.mean([(a-p)**2 for a, p in zip(actual_steps, pred)]))
        pct = I_val / H_actual * 100
        print(f"{name:>20} | {I_val:14.4f} | {pct:7.1f}% | {rmse:8.2f}")
    
    # 相关系数
    print(f"\n相关系数:")
    for name, pred in [("log₂(n)", pred_naive), ("trailing+CRS", pred_improved)]:
        corr = np.corrcoef(actual_steps, pred)[0, 1]
        print(f"  {name}: r = {corr:.4f}")
    
    # ρ的层次结构
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║ 预测密度ρ的层次结构                                        ║
╠══════════════════════════════════════════════════════════════╣
║ 层次           │ 预测目标      │ ρ值          │ 信息捕获    ║
╠══════════════════════════════════════════════════════════════╣
║ 微观（单步CRS）│ CRS长度       │ 2.00 bits/op │ 100%        ║
║ 中观（首CRS）  │ 第一个k       │ ~2.0 bits/op │ 100%        ║
║ 宏观（停止时间）│ 总步数        │ ~{I_improved/3:.2f} bits/op │ {I_improved/H_actual*100:.1f}%       ║
╚══════════════════════════════════════════════════════════════╝

关键洞察：
ρ从微观到宏观的衰减 ≈ 100% → {I_improved/H_actual*100:.0f}%
这是因为轨迹是CRS-Drop周期的序列组合，
虽然每个周期的微观结构被完美理解，
但周期间的非线性组合导致宏观预测力大幅下降。

这类似于物理学中的"涌现"：
微观规则确定 → 宏观行为不可精确预测
""")

if __name__ == "__main__":
    compute_improved_rho()
