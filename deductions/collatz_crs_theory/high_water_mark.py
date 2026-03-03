#!/usr/bin/env python3
"""
高水位分析 — 轨迹上升的幅度与持续时间
=============================================
关键问题：轨迹能上升多高？上升持续多久？
这直接关系到Collatz猜想的可证明性。
"""
import numpy as np
import math
from collections import defaultdict

def T_acc(n):
    m = 3 * n + 1
    while m % 2 == 0:
        m //= 2
    return m

def trajectory_stats(n, max_steps=10000):
    """计算轨迹的关键统计量"""
    if n <= 1: return None
    
    current = n if n % 2 == 1 else T_acc(n)  # 确保奇数
    peak = current
    log_start = math.log2(current)
    log_peak = log_start
    peak_step = 0
    
    steps = 0
    first_below = -1  # 第一次低于起点的步数
    
    while current > 1 and steps < max_steps:
        current = T_acc(current)
        steps += 1
        log_current = math.log2(current)
        
        if log_current > log_peak:
            log_peak = log_current
            peak = current
            peak_step = steps
        
        if first_below < 0 and current < n:
            first_below = steps
    
    if current > 1:
        return None  # 没有收敛
    
    return {
        'n': n,
        'log_n': log_start,
        'peak': peak,
        'log_peak': log_peak,
        'excursion': log_peak - log_start,  # 上升高度（log尺度）
        'peak_step': peak_step,
        'total_steps': steps,
        'first_below': first_below,
    }

def analyze_excursions(N=500000):
    """分析轨迹偏移（上升高度）的分布"""
    print("=" * 70)
    print("轨迹偏移分析: 上升高度 vs 起始值")
    print("=" * 70)
    
    stats = []
    for n in range(3, N, 2):
        s = trajectory_stats(n)
        if s:
            stats.append(s)
    
    # 按log₂(n)分组
    log_bins = defaultdict(list)
    for s in stats:
        bin_idx = int(s['log_n'])
        log_bins[bin_idx].append(s)
    
    print(f"\n{'log₂(n)':>8} | {'count':>6} | {'平均偏移':>8} | {'最大偏移':>8} | {'偏移/log₂':>10} | {'最大偏移数':>12}")
    print("-" * 72)
    
    max_excursion_overall = 0
    max_excursion_n = 0
    
    for log_bin in sorted(log_bins.keys()):
        entries = log_bins[log_bin]
        excursions = [e['excursion'] for e in entries]
        max_exc = max(excursions)
        max_exc_entry = max(entries, key=lambda x: x['excursion'])
        mean_exc = np.mean(excursions)
        ratio = max_exc / (log_bin + 0.5) if log_bin > 0 else 0
        
        if max_exc > max_excursion_overall:
            max_excursion_overall = max_exc
            max_excursion_n = max_exc_entry['n']
        
        print(f"{log_bin:8d} | {len(entries):6d} | {mean_exc:8.2f} | {max_exc:8.2f} | {ratio:10.3f} | {max_exc_entry['n']:12d}")
    
    print(f"\n全局最大偏移: {max_excursion_overall:.2f} (n={max_excursion_n})")
    
    # 偏移与log₂(n)的关系
    log_ns = np.array([s['log_n'] for s in stats])
    excursions = np.array([s['excursion'] for s in stats])
    
    # 线性拟合
    coeffs = np.polyfit(log_ns, excursions, 1)
    print(f"\n线性拟合: excursion ≈ {coeffs[0]:.4f} × log₂(n) + {coeffs[1]:.4f}")
    print(f"R² = {1 - np.var(excursions - np.polyval(coeffs, log_ns)) / np.var(excursions):.4f}")
    
    # 最大偏移的增长率
    max_by_log = {}
    for s in stats:
        log_bin = int(s['log_n'])
        if log_bin not in max_by_log or s['excursion'] > max_by_log[log_bin]:
            max_by_log[log_bin] = s['excursion']
    
    log_bins_arr = sorted(max_by_log.keys())
    if len(log_bins_arr) > 3:
        max_excs = [max_by_log[k] for k in log_bins_arr]
        coeffs2 = np.polyfit(log_bins_arr, max_excs, 1)
        print(f"\n最大偏移增长率: max_excursion ≈ {coeffs2[0]:.4f} × log₂(n) + {coeffs2[1]:.4f}")
    
    return stats

def analyze_stopping_time_vs_excursion(stats):
    """停止时间与偏移的关系"""
    print("\n" + "=" * 70)
    print("停止时间 vs 偏移高度")
    print("=" * 70)
    
    steps = np.array([s['total_steps'] for s in stats])
    excursions = np.array([s['excursion'] for s in stats])
    log_ns = np.array([s['log_n'] for s in stats])
    
    # 标准化
    norm_steps = steps / log_ns
    
    corr = np.corrcoef(excursions, norm_steps)[0, 1]
    print(f"\ncorr(excursion, steps/log₂(n)) = {corr:.4f}")
    
    # 偏移与首次低于起点的关系
    first_belows = np.array([s['first_below'] for s in stats if s['first_below'] > 0])
    exc_with_fb = np.array([s['excursion'] for s in stats if s['first_below'] > 0])
    
    if len(first_belows) > 0:
        corr2 = np.corrcoef(exc_with_fb, first_belows)[0, 1]
        print(f"corr(excursion, first_below_step) = {corr2:.4f}")
        print(f"E[first_below_step] = {np.mean(first_belows):.2f}")

def analyze_terras_density(N=200000):
    """
    Terras(1976)定义的"有限停止时间"密度
    σ(N) = #{n ≤ N : n有有限停止时间} / N
    
    Terras证明了 σ(N) → 1 当 N → ∞
    我们验证这个收敛速率。
    """
    print("\n" + "=" * 70)
    print("Terras密度验证")
    print("=" * 70)
    
    # 停止时间：第一次 T^k(n) < n
    checkpoints = [1000, 5000, 10000, 50000, 100000, 200000]
    
    count_with_stopping = 0
    total = 0
    
    results = []
    
    for n in range(2, N + 1):
        total += 1
        current = n
        found = False
        for step in range(1, 1000):
            current = current // 2 if current % 2 == 0 else 3 * current + 1
            if current < n:
                found = True
                break
        if found:
            count_with_stopping += 1
        
        if total in checkpoints:
            density = count_with_stopping / total
            results.append((total, density))
    
    print(f"\n{'N':>10} | {'σ(N)':>12} | {'1-σ(N)':>12}")
    print("-" * 40)
    for n_val, d in results:
        print(f"{n_val:10d} | {d:12.8f} | {1-d:12.8f}")

if __name__ == "__main__":
    stats = analyze_excursions(N=200000)
    analyze_stopping_time_vs_excursion(stats)
    analyze_terras_density()
