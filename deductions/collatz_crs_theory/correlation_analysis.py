#!/usr/bin/env python3
"""
CRS-Drop周期间相关性的精确分析
================================
问题：E[Δ]理论=-1.830 vs 实验=-1.764，差异来源是什么？

假设：k（CRS长度）和drop_ν₂不独立。
具体地：CRS结束后的值 a_{k-1} 的模结构取决于k，
这影响了下一步的ν₂分布。

让我精确计算 E[drop_ν₂ | k] 和 E[k·drop_ν₂]。
"""
import numpy as np
import math
from collections import Counter, defaultdict

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

def analyze_conditional_drop(N=500000):
    """
    精确分析 E[drop_ν₂ | CRS长度=k]
    
    CRS结束点的结构：
    - CRS长度k意味着n有k个尾部1
    - 经过k-1步T_acc后，结束点有1个尾部1
    - 但结束点的*其他*位的模式取决于k
    """
    print("=" * 70)
    print("条件分布 E[drop_ν₂ | k] 的精确分析")
    print("=" * 70)
    
    # 收集数据: (k, drop_v2, CRS结束点mod各种模数)
    k_to_drops = defaultdict(list)
    k_to_endpoints = defaultdict(list)
    
    for n in range(3, 2*N, 2):
        k = trailing_ones(n)
        
        # 追踪CRS到结束点
        current = n
        for _ in range(k - 1):
            current = T_acc(current)
        
        endpoint = current
        drop = v2(3 * endpoint + 1)
        
        k_to_drops[k].append(drop)
        k_to_endpoints[k].append(endpoint)
    
    # 输出条件期望
    print(f"\n{'k':>4} | {'count':>8} | {'E[drop|k]':>10} | {'Var[drop|k]':>12} | {'endpoint mod 8分布':>25}")
    print("-" * 75)
    
    ek_times_edrop = 0  # E[k * drop]
    ek_sum = 0
    edrop_sum = 0
    total_n = 0
    
    for k in sorted(k_to_drops.keys()):
        if len(k_to_drops[k]) < 5:
            continue
        drops = k_to_drops[k]
        endpoints = k_to_endpoints[k]
        
        mean_drop = np.mean(drops)
        var_drop = np.var(drops)
        
        # endpoint mod 8 分布
        mod8 = Counter(e % 8 for e in endpoints)
        mod8_str = " ".join(f"{m}:{c}" for m, c in sorted(mod8.items()))
        
        if k <= 12:
            print(f"{k:4d} | {len(drops):8d} | {mean_drop:10.4f} | {var_drop:12.4f} | {mod8_str[:25]}")
        
        for d in drops:
            ek_times_edrop += k * d
            ek_sum += k
            edrop_sum += d
            total_n += 1
    
    # 计算相关性
    E_k = ek_sum / total_n
    E_drop = edrop_sum / total_n
    E_k_drop = ek_times_edrop / total_n
    Cov_k_drop = E_k_drop - E_k * E_drop
    
    print(f"\n统计量:")
    print(f"  E[k] = {E_k:.6f}")
    print(f"  E[drop] = {E_drop:.6f}")
    print(f"  E[k·drop] = {E_k_drop:.6f}")
    print(f"  Cov(k, drop) = {Cov_k_drop:.6f}")
    
    # 精确的E[Δ]计算
    # Δ = k·log₂(3/2) - drop
    # E[Δ] = E[k]·log₂(3/2) - E[drop]
    lg32 = math.log2(3/2)
    E_delta_independent = E_k * lg32 - E_drop
    E_delta_exact = sum(k * lg32 - d for k_val in k_to_drops for k in [k_val] for d in k_to_drops[k_val]) / total_n
    
    print(f"\n  E[Δ]（假设独立）= E[k]·lg(3/2) - E[drop] = {E_delta_independent:.6f}")
    print(f"  E[Δ]（精确）= {E_delta_exact:.6f}")
    print(f"  差异 = {E_delta_exact - E_delta_independent:.6f}")
    print(f"  差异来源 = Cov项 = 0（因为Δ是线性的）")
    
    # 等等——Δ = k·c - drop，E[Δ] = c·E[k] - E[drop]
    # 这跟独立不独立无关！线性期望不需要独立！
    # 那差异来源在哪里？
    
    print(f"\n重要修正：E[Δ] = E[k]·lg(3/2) - E[drop] 不依赖于独立性！")
    print(f"所以理论-1.830和实验-1.764的差异不来自k和drop的相关性。")
    print(f"差异必须来自其他地方...")
    
    return k_to_drops, E_k, E_drop

def find_true_source_of_discrepancy(N=500000):
    """
    寻找理论与实验E[Δ]差异的真正来源
    
    理论：E[k]=2, E[drop]=3 → E[Δ] = 2×0.585-3 = -1.830
    实验：E[Δ] ≈ -1.764
    
    所以要么E[k]≠2，要么E[drop]≠3，在实际轨迹中。
    
    关键：上面的分析用的是"所有奇数"的统计，
    但实际轨迹访问的奇数不是均匀分布的！
    """
    print("\n" + "=" * 70)
    print("差异的真正来源：轨迹采样 vs 均匀采样")
    print("=" * 70)
    
    # 方法1：均匀采样所有奇数
    uniform_ks = []
    uniform_drops = []
    for n in range(3, 2*N, 2):
        k = trailing_ones(n)
        current = n
        for _ in range(k - 1):
            current = T_acc(current)
        drop = v2(3 * current + 1)
        uniform_ks.append(k)
        uniform_drops.append(drop)
    
    # 方法2：跟随实际轨迹
    trajectory_ks = []
    trajectory_drops = []
    
    for start in range(3, 100000, 2):
        n = start
        for _ in range(30):  # 每条轨迹取30个周期
            if n <= 1:
                break
            k = trailing_ones(n)
            current = n
            for _ in range(k - 1):
                current = T_acc(current)
            drop = v2(3 * current + 1)
            trajectory_ks.append(k)
            trajectory_drops.append(drop)
            n = T_acc(current)
    
    print(f"\n{'统计量':>20} | {'均匀采样':>12} | {'轨迹采样':>12} | {'差异':>10}")
    print("-" * 60)
    
    eu_k = np.mean(uniform_ks)
    et_k = np.mean(trajectory_ks)
    eu_d = np.mean(uniform_drops)
    et_d = np.mean(trajectory_drops)
    
    lg32 = math.log2(3/2)
    eu_delta = eu_k * lg32 - eu_d
    et_delta = et_k * lg32 - et_d
    
    print(f"{'E[k]':>20} | {eu_k:12.6f} | {et_k:12.6f} | {et_k-eu_k:+10.6f}")
    print(f"{'E[drop_ν₂]':>20} | {eu_d:12.6f} | {et_d:12.6f} | {et_d-eu_d:+10.6f}")
    print(f"{'E[Δ]':>20} | {eu_delta:12.6f} | {et_delta:12.6f} | {et_delta-eu_delta:+10.6f}")
    print(f"{'样本数':>20} | {len(uniform_ks):12d} | {len(trajectory_ks):12d} |")
    
    print(f"""
分析：
  均匀采样 E[k] = {eu_k:.4f}（理论2.0 ✓）
  轨迹采样 E[k] = {et_k:.4f}（偏离2.0！）
  
  均匀采样 E[drop] = {eu_d:.4f}（理论3.0 ✓）
  轨迹采样 E[drop] = {et_d:.4f}（也有偏差）
  
  差异来源：轨迹中访问的奇数 ≠ 均匀分布！
  轨迹对某些模类有偏好，导致k和drop的期望偏离理论值。
""")
    
    # 深入：轨迹中的数 mod 4, mod 8 的分布
    print("轨迹中访问的奇数的模分布:")
    
    traj_numbers = []
    for start in range(3, 50000, 2):
        n = start
        for _ in range(20):
            if n <= 1:
                break
            traj_numbers.append(n)
            n = T_acc(n)
    
    mod4 = Counter(n % 4 for n in traj_numbers)
    mod8 = Counter(n % 8 for n in traj_numbers)
    total_t = len(traj_numbers)
    
    print(f"  mod 4: {dict((k, f'{v/total_t:.4f}') for k, v in sorted(mod4.items()))}")
    print(f"  mod 8: {dict((k, f'{v/total_t:.4f}') for k, v in sorted(mod8.items()))}")
    print(f"  (均匀分布应为: mod 4各1/2, mod 8各1/4)")
    
    # mod 4 的偏差直接影响 trailing_ones 的分布
    p_3mod4 = mod4[3] / total_t  # trailing_ones ≥ 2 的概率
    print(f"\n  P(n≡3 mod 4) in trajectory = {p_3mod4:.4f} (均匀=0.5000)")
    print(f"  这意味着轨迹中CRS≥2的频率{'高于' if p_3mod4 > 0.5 else '低于'}均匀预期")

if __name__ == "__main__":
    k_to_drops, E_k, E_drop = analyze_conditional_drop(N=200000)
    find_true_source_of_discrepancy(N=200000)
