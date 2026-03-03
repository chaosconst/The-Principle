#!/usr/bin/env python3
"""
Collatz猜想的统计力学分析
==========================
核心问题：虽然单个CRS-drop周期可能净上升，
但长期统计效果是否保证收敛？

方法：将加速Collatz映射视为随机游走，
分析log₂(n)的长期漂移。
"""
import numpy as np
import math
from collections import Counter, defaultdict

def v2(n):
    if n == 0: return -1
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

def analyze_long_term_drift():
    """
    分析加速Collatz映射在log₂尺度上的长期行为。
    
    每一步 T_acc: log₂(T_acc(n)) - log₂(n) = log₂(3) - ν₂(3n+1)
    
    关键：ν₂(3n+1)的分布取决于n mod 2^k，而这个分布
    在Collatz轨迹中不是均匀的——它有记忆效应。
    
    但是！我们的CRS定理告诉我们：
    - CRS期间每步恰好ν₂=1，贡献 log₂(3)-1 = +0.585
    - CRS结束后第一步ν₂≥2
    
    所以正确的分析不是逐步，而是按"CRS-drop"周期。
    """
    print("=" * 70)
    print("长期漂移分析：CRS-Drop周期视角")
    print("=" * 70)
    
    # 一个CRS-Drop周期：
    # 1. CRS上升k步（k ~ Geom(1/2)），每步+log₂(3/2)
    # 2. Drop步，ν₂ = ν₂(3·a_{k-1}+1)
    # 
    # 周期净效果 = k·log₂(3/2) - ν₂(终止)
    # 
    # 但ν₂(终止)不是简单的Geom(1/2)——
    # 它取决于CRS结束点的2-adic结构
    
    # 实验：收集大量CRS-Drop周期的统计
    cycle_data = []  # (k, drop_v2, net_effect)
    
    n = 3
    steps = 0
    max_steps = 2000000
    
    while steps < max_steps and n > 1:
        # 一个CRS-Drop周期
        k = trailing_ones(n)  # CRS长度
        
        # 执行CRS
        current = n
        for _ in range(k - 1):
            current = T_acc(current)
        
        # Drop步
        drop_v2 = v2(3 * current + 1)
        next_n = T_acc(current)
        
        net = k * math.log2(3/2) - drop_v2
        cycle_data.append((k, drop_v2, net))
        
        n = next_n
        steps += 1
        
        if steps > max_steps:
            break
    
    print(f"\n从n=3开始追踪了 {len(cycle_data)} 个CRS-Drop周期")
    print(f"最终n = {n}")
    
    # 统计
    ks = [d[0] for d in cycle_data]
    drops = [d[1] for d in cycle_data]
    nets = [d[2] for d in cycle_data]
    
    print(f"\n--- CRS长度统计 ---")
    print(f"E[k] = {np.mean(ks):.4f} (理论 2.0)")
    print(f"Var[k] = {np.var(ks):.4f} (理论 2.0)")
    
    print(f"\n--- Drop ν₂ 统计 ---")
    print(f"E[drop_ν₂] = {np.mean(drops):.4f}")
    print(f"Var[drop_ν₂] = {np.var(drops):.4f}")
    
    print(f"\n--- 净效果统计 ---")
    print(f"E[net] = {np.mean(nets):.6f}")
    print(f"Var[net] = {np.var(nets):.4f}")
    print(f"净效果>0的比例 = {sum(1 for x in nets if x > 0)/len(nets)*100:.2f}%")
    
    # 理论分析
    print(f"\n--- 理论比较 ---")
    # E[net] = E[k]·log₂(3/2) - E[drop_ν₂]
    theoretical_net = np.mean(ks) * math.log2(3/2) - np.mean(drops)
    print(f"E[k]·log₂(3/2) - E[drop_ν₂] = {theoretical_net:.6f}")
    print(f"直接测量 E[net] = {np.mean(nets):.6f}")
    
    # 如果k和drop_v2独立：
    # E[net] = 2 × 0.585 - E[drop_v2]
    # 所以E[drop_v2]的值是关键！
    
    # 按k分组看drop_v2
    print(f"\n--- 按CRS长度分组的Drop ν₂ ---")
    k_groups = defaultdict(list)
    for k, dv, _ in cycle_data:
        k_groups[k].append(dv)
    
    print(f"{'k':>4} | {'count':>8} | {'E[drop_ν₂]':>12} | {'净效果':>10}")
    print("-" * 45)
    for k in sorted(k_groups.keys()):
        if len(k_groups[k]) < 3:
            continue
        mean_dv = np.mean(k_groups[k])
        net_k = k * math.log2(3/2) - mean_dv
        print(f"{k:4d} | {len(k_groups[k]):8d} | {mean_dv:12.4f} | {net_k:10.4f}")
    
    return cycle_data

def analyze_from_many_starting_points():
    """
    从多个起点分析CRS-Drop周期，避免单条轨迹的偏差
    """
    print("\n" + "=" * 70)
    print("多起点CRS-Drop分析")
    print("=" * 70)
    
    all_nets = []
    
    # 从不同起点采样
    for start in range(3, 100000, 2):
        n = start
        for _ in range(20):  # 每条轨迹只取20个周期
            if n <= 1:
                break
            k = trailing_ones(n)
            current = n
            for _ in range(k - 1):
                current = T_acc(current)
            drop_v2 = v2(3 * current + 1)
            net = k * math.log2(3/2) - drop_v2
            all_nets.append(net)
            n = T_acc(current)
    
    print(f"总周期数: {len(all_nets)}")
    print(f"E[net_per_cycle] = {np.mean(all_nets):.6f}")
    print(f"Std[net] = {np.std(all_nets):.4f}")
    print(f"净正比例: {sum(1 for x in all_nets if x > 0)/len(all_nets)*100:.2f}%")
    
    # 关键：每个CRS-Drop周期涉及k+1步T_acc
    # 所以每步的平均漂移 = E[net] / E[k+1]
    # 但更好的度量是每CRS-Drop周期的漂移
    
    cumsum = np.cumsum(all_nets)
    print(f"\n累积漂移最终值: {cumsum[-1]:.2f}")
    print(f"每周期平均漂移: {cumsum[-1]/len(all_nets):.6f}")
    
    # 这应该是负的!
    
def theoretical_expected_drop():
    """
    理论计算 E[drop_ν₂ | CRS终止]
    
    CRS终止时，最后一个值 a_{k-1} 满足 a_{k-1} ≡ 1 (mod 4)
    （因为trailing_ones = 1，意味着末尾是 ...01）
    
    3·a_{k-1}+1 ≡ 3·1+1 = 4 ≡ 0 (mod 4) 当 a_{k-1} ≡ 1 mod 4
    3·a_{k-1}+1 mod 8:
      a_{k-1} ≡ 1 mod 8: 3+1=4, ν₂≥2
      a_{k-1} ≡ 5 mod 8: 15+1=16, ν₂≥4
    
    等等这不对，CRS终止时的值不是有1个trailing one——
    它有恰好1个trailing one（因为CRS从k个1减到1个1就停）
    
    所以终止点 a_{k-1} 的二进制末尾是 ...01
    即 a_{k-1} ≡ 1 (mod 4)
    
    那么 ν₂(3·a_{k-1}+1) 的分布是什么？
    需要知道 a_{k-1} mod 2^m 的分布。
    """
    print("\n" + "=" * 70)
    print("CRS终止点的2-adic结构")
    print("=" * 70)
    
    # 收集CRS终止点的模结构
    end_points = []
    for n in range(3, 400000, 2):
        k = trailing_ones(n)
        if k >= 2:  # 至少有一个CRS步
            current = n
            for _ in range(k - 1):
                current = T_acc(current)
            end_points.append(current)
    
    # 分析终止点 mod 2^m
    print(f"\n收集了 {len(end_points)} 个CRS终止点")
    
    # 检查 mod 4
    mod4 = Counter(p % 4 for p in end_points)
    print(f"\n终止点 mod 4: {dict(sorted(mod4.items()))}")
    print("(应全为1，因为trailing_ones=1)")
    
    # 检查 mod 8
    mod8 = Counter(p % 8 for p in end_points)
    print(f"终止点 mod 8: {dict(sorted(mod8.items()))}")
    
    # 检查 mod 16
    mod16 = Counter(p % 16 for p in end_points)
    print(f"终止点 mod 16: {dict(sorted(mod16.items()))}")
    
    # 这些终止点的ν₂(3p+1)分布
    drop_v2s = [v2(3*p+1) for p in end_points]
    c = Counter(drop_v2s)
    total = len(drop_v2s)
    print(f"\nν₂(3·终止点+1) 分布:")
    for k in sorted(c.keys()):
        print(f"  ν₂={k}: {c[k]:6d} ({c[k]/total*100:.2f}%)")
    
    print(f"\nE[drop_ν₂] = {np.mean(drop_v2s):.6f}")
    
    # 理论：如果终止点均匀分布在 ≡1 mod 4 的奇数中
    # P(ν₂(3n+1)=k | n≡1 mod 4) = ?
    # n≡1 mod 4: 3n+1 ≡ 4 mod 12, 所以 ν₂≥2
    # n≡1 mod 8: 3+1=4, ν₂(4)=2
    # n≡5 mod 8: 15+1=16, ν₂(16)=4
    
    print(f"\n理论检查:")
    print("n≡1(mod 4)的奇数中ν₂(3n+1)的条件分布:")
    
    theory_v2 = Counter()
    for n in range(1, 400000, 4):  # n≡1 mod 4
        theory_v2[v2(3*n+1)] += 1
    total_t = sum(theory_v2.values())
    for k in sorted(theory_v2.keys()):
        print(f"  ν₂={k}: {theory_v2[k]/total_t*100:.2f}%")
    print(f"  E[ν₂|n≡1 mod 4] = {sum(k*v for k,v in theory_v2.items())/total_t:.6f}")

if __name__ == "__main__":
    cycle_data = analyze_long_term_drift()
    print()
    analyze_from_many_starting_points()
    print()
    theoretical_expected_drop()
