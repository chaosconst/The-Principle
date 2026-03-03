#!/usr/bin/env python3
"""
CRS核心定理 — 完整证明
========================

定理: 对任意奇数 n ≥ 1，加速Collatz映射下的
连续上升序列长度 CRS(n) 等于 n 的二进制尾部连续1的个数。

证明:
设 n 的二进制表示末尾有 k 个连续的 1。
即 n = m · 2^k + (2^k - 1)，其中 m 是某个非负整数且 m 的最低位是 0
（或者 n = 2^k - 1 即 Mersenne 数的情况下 m = 0）。

引理: 若 n ≡ 2^j - 1 (mod 2^j) 对某个 j ≥ 1，
则 CRS 的前 j 步中每步都有 ν₂(3·current+1) = 1。

证明引理:
我们用归纳法证明：CRS的第i步 (0 ≤ i < k) 的值 aᵢ 满足
aᵢ ≡ 2^{k-i} - 1 (mod 2^{k-i})
即 aᵢ 的末尾有 k-i 个连续的 1。

基础: a₀ = n，末尾有 k 个 1。✓

递推: 若 aᵢ 末尾有 k-i ≥ 2 个 1，
则 aᵢ ≡ 3 (mod 4)，所以 ν₂(3aᵢ+1) = 1。
aᵢ₊₁ = (3aᵢ+1)/2。

关键: (3aᵢ+1)/2 末尾有几个 1?
设 aᵢ = ...b₂b₁ 11...1 (末尾 k-i 个 1，然后是 0)
        ↑ 这个位是 0
即 aᵢ = A·2^{k-i} + (2^{k-i} - 1)，A 为偶数

3aᵢ + 1 = 3A·2^{k-i} + 3(2^{k-i} - 1) + 1 = 3A·2^{k-i} + 3·2^{k-i} - 2
        = (3A + 3)·2^{k-i} - 2 = 2·((3A+3)·2^{k-i-1} - 1)

(3aᵢ+1)/2 = (3A+3)·2^{k-i-1} - 1

当 k-i-1 ≥ 1 (即 i ≤ k-2):
  (3A+3)·2^{k-i-1} 是偶数
  减1后末尾有 k-i-1 个 1
  所以 aᵢ₊₁ 末尾有 k-i-1 个 1 ✓

当 i = k-1:
  aᵢ 末尾只有 1 个 1 (即 aᵢ ≡ 1 mod 2 但 aᵢ ≡ 3 mod 4? 不对...)
  aᵢ 末尾有 k-(k-1) = 1 个 1
  所以 aᵢ ≡ 1 (mod 4)（末尾是 ...01）
  这意味着 ν₂(3aᵢ+1) ≥ 2，CRS 终止 ✓

等等，末尾 1 个 1 意味着 aᵢ 是奇数但 aᵢ ≡ 1 (mod 4)。
这确实意味着 3aᵢ+1 ≡ 3+1 = 4 ≡ 0 (mod 4)，ν₂ ≥ 2。
"""
import numpy as np
from collections import Counter

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

def verify_trailing_ones_theorem(N=500000):
    """大规模验证定理"""
    print("=" * 70)
    print("定理验证: CRS(n) = trailing_ones(n)")
    print("=" * 70)
    
    mismatches = 0
    for n in range(1, N, 2):
        # CRS长度
        crs = 1
        current = n
        for _ in range(60):
            tn = T_acc(current)
            if tn > current:
                crs += 1
                current = tn
            else:
                break
        
        t1 = trailing_ones(n)
        if crs != t1:
            mismatches += 1
            if mismatches <= 5:
                print(f"  反例: n={n}, bin={bin(n)}, CRS={crs}, trailing_ones={t1}")
    
    total = N // 2
    print(f"\n验证范围: 奇数 1 到 {N-1}，共 {total} 个")
    print(f"不匹配数: {mismatches}")
    print(f"匹配率: {(total-mismatches)/total*100:.6f}%")
    
    if mismatches == 0:
        print("\n✓ 定理在验证范围内完美成立")

def verify_induction_step(N=100000):
    """验证归纳步骤: 如果aᵢ末尾有m≥2个1，则aᵢ₊₁末尾有m-1个1"""
    print("\n" + "=" * 70)
    print("归纳步骤验证: trailing_ones减少1")
    print("=" * 70)
    
    mismatches = 0
    total = 0
    
    for n in range(3, N, 2):
        t_n = trailing_ones(n)
        if t_n >= 2:  # CRS继续
            tn = T_acc(n)
            t_tn = trailing_ones(tn)
            total += 1
            if t_tn != t_n - 1:
                mismatches += 1
                if mismatches <= 10:
                    print(f"  n={n}, bin={bin(n)}, t1(n)={t_n}, T_acc={tn}, bin(T)={bin(tn)}, t1(T)={t_tn}")
    
    print(f"\n检查了 {total} 个有CRS≥2的奇数")
    print(f"不匹配数: {mismatches}")
    
    if mismatches == 0:
        print("✓ 归纳步骤完美成立: T_acc减少恰好1个尾部1")

def crs_distribution_theory():
    """CRS分布的完整理论解释"""
    print("\n" + "=" * 70)
    print("CRS ~ Geom(1/2) 的完整解释")
    print("=" * 70)
    
    print("""
完整推导:

1. CRS(n) = trailing_ones(n)  [已证明的定理]

2. 对于在 [1, N] 中均匀随机的奇数 n:
   
   trailing_ones(n) = k 当且仅当 n 的二进制是 ...0_underbrace{11...1}_{k个}
   
   P(trailing_ones ≥ 1) = 1 (因为n是奇数，末位必是1)
   P(trailing_ones ≥ 2) = P(倒数第2位=1) = 1/2
   P(trailing_ones ≥ 3) = P(倒数第2,3位都=1) = 1/4
   一般: P(trailing_ones ≥ k) = (1/2)^{k-1}
   
   因此: P(trailing_ones = k) = P(≥k) - P(≥k+1) 
        = (1/2)^{k-1} - (1/2)^k = (1/2)^k
   
   这精确是 Geom(1/2) 分布 ✓

3. 推论:
   E[CRS] = sum_{k=1}^∞ k/2^k = 2
   Var[CRS] = 2
   P(CRS ≥ k) = (1/2)^{k-1}

4. 最大CRS长度预测:
   在N个奇数中, max CRS ≈ log₂(N)
   因为 P(CRS ≥ log₂(N)) ≈ 1/N, 
   期望有约1个数达到CRS=log₂(N)

这完全解释了之前观测到的:
- CRS长度比例是完美的 2:1 递减
- 最大CRS/log₂(N) 比率趋近1.0
- 所有CRS记录保持者是Mersenne数(全1)
""")

def analyze_post_crs_behavior(N=200000):
    """
    CRS结束后发生什么？
    这是理解Collatz收敛的关键——CRS上升后必须有足够的下降来补偿。
    """
    print("\n" + "=" * 70)
    print("CRS后的下降分析(关键!)")
    print("=" * 70)
    
    # 对于CRS长度为k的数，CRS结束时上升了 k·log₂(3/2)
    # 然后ν₂(3·last+1) ≥ 2，下降至少 2·log₂(2) = 2
    # 净效果是什么？
    
    results_by_k = {}
    
    for n in range(3, 2*N, 2):
        k = trailing_ones(n)
        if k not in results_by_k:
            results_by_k[k] = {'count': 0, 'net_gains': [], 'first_drop_v2': []}
        
        # 追踪CRS
        current = n
        for _ in range(k - 1):
            current = T_acc(current)
        
        # CRS结束点
        crs_end = current
        
        # CRS结束后的第一步
        next_val = T_acc(crs_end)
        drop_v2 = v2(3 * crs_end + 1)  # 终止CRS的ν₂
        
        # 净增益 = log₂(next_val / n)
        import math
        net_log = math.log2(next_val / n) if next_val > 0 and n > 0 else 0
        
        results_by_k[k]['count'] += 1
        results_by_k[k]['net_gains'].append(net_log)
        results_by_k[k]['first_drop_v2'].append(drop_v2)
    
    print(f"\n{'CRS k':>6} | {'数量':>8} | {'CRS上升':>10} | {'终止ν₂均值':>10} | {'净log₂增益':>12} | {'净效果':>8}")
    print("-" * 72)
    
    for k in sorted(results_by_k.keys()):
        if k > 15 or results_by_k[k]['count'] < 5:
            continue
        d = results_by_k[k]
        crs_rise = k * math.log2(3/2)  # 上升量
        mean_v2 = np.mean(d['first_drop_v2'])
        mean_net = np.mean(d['net_gains'])
        effect = "净升" if mean_net > 0 else "净降"
        
        print(f"{k:6d} | {d['count']:8d} | {crs_rise:10.4f} | {mean_v2:10.4f} | {mean_net:12.4f} | {effect:>8}")
    
    # 关键问题：CRS后一步的净效果是否总是负的？
    print(f"""
关键分析:
- CRS长度k产生的上升 = k × log₂(3/2) = k × 0.5850
- CRS终止步的下降 = ν₂(终止) × log₂(2) = ν₂(终止)
- CRS一个完整"上升-下降"周期的净效果 = k×0.585 - ν₂(终止)

如果净效果总是负的，则轨迹必然收敛！
但如果某些情况下净效果为正，就需要更长期的分析。
""")

if __name__ == "__main__":
    verify_trailing_ones_theorem()
    verify_induction_step()
    crs_distribution_theory()
    analyze_post_crs_behavior()
