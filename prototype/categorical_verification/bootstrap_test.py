#!/usr/bin/env python3
"""
Bootstrap置信区间：验证 ρ_CA < ρ_SelfRef
正确方法：多次独立运行每个系统，比较ρ的分布
"""
import numpy as np
from collections import Counter
import time

def entropy(sequence):
    counts = Counter(sequence)
    total = len(sequence)
    h = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            h -= p * np.log2(p)
    return h

def mutual_information(seq_x, seq_y):
    hx = entropy(seq_x)
    hy = entropy(seq_y)
    pairs = list(zip(seq_x, seq_y))
    hxy = entropy(pairs)
    return max(0.0, hx + hy - hxy)

def run_ca(n_steps, noise_level, width=32, seed=None):
    if seed is not None:
        np.random.seed(seed)
    rule = 110
    state = np.zeros(width, dtype=int)
    state[width//2] = 1
    ops = width * 3
    flip_prob = min(noise_level * 0.02, 0.5)
    states = []
    for _ in range(n_steps):
        density = sum(state) / width
        mr = 0; cr = 0
        for b in state:
            if b == 1: cr += 1; mr = max(mr, cr)
            else: cr = 0
        states.append((int(density*32)%32, int(mr/width*16)%16))
        ns = np.zeros(width, dtype=int)
        for i in range(width):
            idx = (state[(i-1)%width]<<2)|(state[i]<<1)|(state[(i+1)%width])
            ns[i] = (rule >> idx) & 1
        if noise_level > 0:
            for i in range(width):
                if np.random.random() < flip_prob:
                    ns[i] = 1 - ns[i]
        state = ns
    mi = mutual_information(states[:-1], states[1:])
    return mi / ops

def run_selfref(n_steps, noise_level, seed=None):
    if seed is not None:
        np.random.seed(seed)
    value, hist_hash = 42, 0
    states = []
    ops = 11
    for _ in range(n_steps):
        states.append((value%32, hist_hash%32))
        combined = (value*7 + hist_hash*13) % 256
        behavior = (combined ^ (combined>>3) ^ (combined<<2)) % 256
        if noise_level > 0:
            noise = int(np.random.normal(0, noise_level*2)) % 256
            behavior = (behavior + noise) % 256
        new_hash = ((hist_hash*31) + behavior + value) % 256
        value, hist_hash = behavior, new_hash
    mi = mutual_information(states[:-1], states[1:])
    return mi / ops

# Bootstrap
N = 10000
n_bootstrap = 50  # 独立运行次数
noise_levels = [0, 1.0, 4.0, 16.0]

print("Bootstrap检验: ρ_CA vs ρ_SelfRef")
print(f"N={N} steps, {n_bootstrap} independent runs per system")
print("=" * 80)

start = time.time()

for nl in noise_levels:
    rhos_ca = []
    rhos_sr = []
    
    for i in range(n_bootstrap):
        rhos_ca.append(run_ca(N, nl, seed=1000+i))
        rhos_sr.append(run_selfref(N, nl, seed=2000+i))
    
    rhos_ca = np.array(rhos_ca)
    rhos_sr = np.array(rhos_sr)
    
    # 检查分布是否重叠
    ca_max = np.max(rhos_ca)
    sr_min = np.min(rhos_sr)
    separated = sr_min > ca_max
    
    # 差异的bootstrap分布
    diffs = rhos_sr - rhos_ca  # 逐对比较
    p_value = np.mean(diffs <= 0)  # P(SR <= CA)
    
    # Cohen's d
    pooled_std = np.sqrt((np.var(rhos_ca) + np.var(rhos_sr)) / 2)
    if pooled_std > 0:
        cohens_d = (np.mean(rhos_sr) - np.mean(rhos_ca)) / pooled_std
    else:
        cohens_d = float('inf')
    
    sig = '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'ns'
    
    print(f"\n  σ = {nl:.1f}:")
    print(f"    CA:      mean={np.mean(rhos_ca):.6f} ± {np.std(rhos_ca):.6f}  range=[{np.min(rhos_ca):.6f}, {np.max(rhos_ca):.6f}]")
    print(f"    SelfRef: mean={np.mean(rhos_sr):.6f} ± {np.std(rhos_sr):.6f}  range=[{np.min(rhos_sr):.6f}, {np.max(rhos_sr):.6f}]")
    print(f"    Δρ mean = {np.mean(diffs):.6f}, p(SR≤CA) = {p_value:.4f} {sig}")
    print(f"    Cohen's d = {cohens_d:.1f}, distributions {'SEPARATED' if separated else 'overlap'}")
    print(f"    Ratio: {np.mean(rhos_sr)/max(np.mean(rhos_ca), 1e-12):.1f}x")

elapsed = time.time() - start
print(f"\n总耗时: {elapsed:.1f}s")
