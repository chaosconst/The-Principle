#!/usr/bin/env python3
"""
Collatz猜想 — 严格数学基础
==========================================
本文件建立Collatz映射的精确数学定义和基本性质。
所有声明都附带证明或精确引用。
"""
import numpy as np
from collections import Counter

# ============================================================
# 第一部分：基本定义
# ============================================================

def T(n):
    """标准Collatz映射 T: Z+ -> Z+
    T(n) = n/2       if n ≡ 0 (mod 2)
    T(n) = 3n+1      if n ≡ 1 (mod 2)
    """
    return n // 2 if n % 2 == 0 else 3 * n + 1

def T_acc(n):
    """加速Collatz映射 (Syracuse映射) T_acc: Odd+ -> Odd+
    T_acc(n) = (3n+1) / 2^{ν₂(3n+1)}
    即：跳过所有除以2的步骤，直接映射到下一个奇数
    """
    assert n % 2 == 1, f"T_acc 需要奇数输入，得到 {n}"
    m = 3 * n + 1
    while m % 2 == 0:
        m //= 2
    return m

def v2(n):
    """2-adic赋值 ν₂(n): n能被2整除的最大次数
    约定：ν₂(0) = ∞ (这里返回-1表示)
    """
    if n == 0: return -1
    c = 0
    while n % 2 == 0:
        c += 1
        n //= 2
    return c

def odd_part(n):
    """奇部分 o(n) = n / 2^{ν₂(n)}"""
    while n % 2 == 0:
        n //= 2
    return n

def trajectory(n, max_steps=10000):
    """计算完整Collatz轨迹直到到达1"""
    path = [n]
    for _ in range(max_steps):
        if n == 1: break
        n = T(n)
        path.append(n)
    return path

def trajectory_acc(n, max_steps=1000):
    """加速轨迹：只记录奇数"""
    assert n % 2 == 1
    path = [n]
    for _ in range(max_steps):
        if n == 1: break
        n = T_acc(n)
        path.append(n)
    return path

def stopping_time(n, max_steps=10000):
    """停止时间：第一次到达小于n的步数"""
    if n <= 1: return 0
    current = n
    for step in range(1, max_steps + 1):
        current = T(current)
        if current < n:
            return step
    return -1  # 未找到

def total_stopping_time(n, max_steps=100000):
    """总停止时间：到达1的步数"""
    if n <= 1: return 0
    current = n
    for step in range(1, max_steps + 1):
        current = T(current)
        if current == 1:
            return step
    return -1

# ============================================================
# 第二部分：已知定理验证
# ============================================================

def verify_v2_distribution(N=100000):
    """
    定理(Everett, 1977; Lagarias, 1985)：
    对于随机均匀选取的奇数n，ν₂(3n+1)的分布精确等于几何分布。
    即 P(ν₂(3n+1) = k) = 1/2^k，对所有 k ≥ 1。
    
    证明：这是因为3n+1 mod 2^k 的分布是均匀的。
    当n为奇数时，3n+1 ≡ 0 (mod 2)总成立。
    3n+1 ≡ 0 (mod 4) 当且仅当 n ≡ 1 (mod 4)，概率1/2。
    一般地，3n+1 ≡ 0 (mod 2^k) 当且仅当 n属于特定模2^k的同余类。
    """
    odds = range(1, 2*N, 2)
    vals = [v2(3*n+1) for n in odds]
    
    mean = np.mean(vals)
    var = np.var(vals)
    
    print("=" * 60)
    print("定理验证: ν₂(3n+1) ~ Geom(1/2)")
    print("=" * 60)
    print(f"样本量: {len(vals)} 个奇数")
    print(f"E[ν₂] = {mean:.6f}  (理论值: 2.0)")
    print(f"Var[ν₂] = {var:.6f}  (理论值: 2.0)")
    print()
    
    c = Counter(vals)
    total = len(vals)
    max_dev = 0
    print(f"{'k':>3} | {'观测P(ν₂=k)':>12} | {'理论P(ν₂=k)':>12} | {'相对误差':>10}")
    print("-" * 50)
    for k in range(1, 15):
        obs = c.get(k, 0) / total
        theory = 1 / (2**k)
        rel_err = abs(obs - theory) / theory if theory > 0 else 0
        max_dev = max(max_dev, rel_err)
        print(f"{k:3d} | {obs:12.6f} | {theory:12.6f} | {rel_err:10.4%}")
    
    print(f"\n最大相对误差: {max_dev:.4%}")
    return mean, var

def verify_log_drift(N=100000):
    """
    定理(Terras, 1976)：
    加速Collatz映射在对数尺度上的期望漂移率为
    E[log₂(T_acc(n)/n)] = E[log₂(3) - ν₂(3n+1)] = log₂(3) - 2 ≈ -0.415
    
    这意味着"典型"轨迹倾向于下降，但不排除长时间上升的可能。
    """
    import math
    odds = [n for n in range(3, 2*N, 2)]
    log_ratios = []
    for n in odds:
        t = T_acc(n)
        log_ratios.append(math.log2(t / n))
    
    mean_drift = np.mean(log_ratios)
    std_drift = np.std(log_ratios)
    theoretical = math.log2(3) - 2
    
    print("\n" + "=" * 60)
    print("定理验证: 对数漂移率")
    print("=" * 60)
    print(f"样本量: {len(log_ratios)}")
    print(f"E[log₂(T_acc/n)] = {mean_drift:.6f}")
    print(f"理论值 log₂(3)-2 = {theoretical:.6f}")
    print(f"标准差 = {std_drift:.6f}")
    print(f"误差 = {abs(mean_drift - theoretical):.8f}")
    
    # 分析漂移率分布
    hist, edges = np.histogram(log_ratios, bins=50)
    print(f"\n正漂移(上升)比例: {sum(1 for x in log_ratios if x > 0)/len(log_ratios)*100:.2f}%")
    print(f"负漂移(下降)比例: {sum(1 for x in log_ratios if x < 0)/len(log_ratios)*100:.2f}%")
    
    return mean_drift, std_drift

def analyze_exceptional_sets(N=100000):
    """
    分析"例外集"——那些使轨迹上升的奇数。
    Terras(1976)证明了"几乎所有"正整数有有限停止时间。
    这里我们精确刻画使得T_acc(n) > n的奇数集合。
    """
    print("\n" + "=" * 60)
    print("例外集分析: T_acc(n) > n 的奇数")
    print("=" * 60)
    
    rising = []  # T_acc(n) > n
    falling = []  # T_acc(n) < n
    
    for n in range(1, 2*N, 2):
        t = T_acc(n)
        if t > n:
            rising.append(n)
        else:
            falling.append(n)
    
    print(f"上升数数量: {len(rising)} ({len(rising)/N*100:.2f}%)")
    print(f"下降数数量: {len(falling)} ({len(falling)/N*100:.2f}%)")
    
    # 上升数的ν₂分析
    rise_v2 = Counter(v2(3*n+1) for n in rising)
    print(f"\n上升数的ν₂分布:")
    for k in sorted(rise_v2.keys()):
        print(f"  ν₂={k}: {rise_v2[k]} ({rise_v2[k]/len(rising)*100:.1f}%)")
    
    # 关键观察：T_acc(n) > n 当且仅当 ν₂(3n+1) = 1
    # 因为 T_acc(n) = (3n+1)/2^v, 而 T_acc(n) > n ⟺ 3n+1 > n·2^v ⟺ 2^v < 3+1/n ⟺ v=1
    v1_count = sum(1 for n in rising if v2(3*n+1) == 1)
    print(f"\n上升数中ν₂=1的比例: {v1_count/len(rising)*100:.2f}% (应为100%)")
    
    # 上升数的mod 4残基
    mod4 = Counter(n % 4 for n in rising)
    print(f"\n上升数 mod 4 分布:")
    for k in sorted(mod4.keys()):
        print(f"  n ≡ {k} (mod 4): {mod4[k]} ({mod4[k]/len(rising)*100:.1f}%)")
    
    # 理论：n ≡ 3 (mod 4) ⟹ ν₂(3n+1) = 1 ⟹ T_acc(n) = (3n+1)/2 > n
    print(f"\n理论验证: n ≡ 3 (mod 4) 的奇数恰好是所有上升数")
    
    return rising, falling

if __name__ == "__main__":
    print("Collatz猜想 — 严格数学基础")
    print("=" * 60)
    
    verify_v2_distribution()
    verify_log_drift()
    analyze_exceptional_sets()
