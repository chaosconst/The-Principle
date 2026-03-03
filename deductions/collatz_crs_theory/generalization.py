#!/usr/bin/env python3
"""
CRS定理的一般化探索
====================
Collatz映射 T(n) = (3n+1)/2^{v2(3n+1)} 的CRS=trailing_ones定理
是否推广到一般的 ax+b 映射？

考虑一般映射 T_{a,b}(n) = (an+b)/2^{v2(an+b)}
对于奇数 a 和偶数 b（确保映射保持奇数性）。

经典Collatz: a=3, b=1
其他情况: a=5,b=1; a=3,b=3; a=7,b=1 等
"""

def v2(n):
    if n == 0: return -1
    c = 0
    while n % 2 == 0:
        c += 1
        n //= 2
    return c

def T_gen(n, a, b):
    """一般化加速映射"""
    m = a * n + b
    while m % 2 == 0:
        m //= 2
    return m

def trailing_ones(n):
    c = 0
    while n & 1:
        c += 1
        n >>= 1
    return c

def crs_length(n, a, b, max_iter=100):
    """CRS长度"""
    L = 1
    current = n
    for _ in range(max_iter):
        tn = T_gen(current, a, b)
        if tn > current:
            L += 1
            current = tn
        else:
            break
    return L

def test_generalization(a, b, N=50000):
    """测试 CRS = trailing_ones 是否对 (a,b) 成立"""
    matches = 0
    total = 0
    mismatches = []
    
    for n in range(1, N, 2):
        crs = crs_length(n, a, b)
        t1 = trailing_ones(n)
        total += 1
        if crs == t1:
            matches += 1
        elif len(mismatches) < 5:
            mismatches.append((n, crs, t1))
    
    match_rate = matches / total * 100
    return match_rate, mismatches

def analyze_generalization():
    """系统分析不同(a,b)的CRS结构"""
    print("=" * 70)
    print("CRS = trailing_ones 定理的一般化测试")
    print("=" * 70)
    
    # 测试不同的 (a, b) 组合
    cases = [
        (3, 1, "经典Collatz"),
        (5, 1, "5n+1"),
        (5, 3, "5n+3"),
        (7, 1, "7n+1"),
        (7, 3, "7n+3"),
        (3, 3, "3n+3"),
        (3, 5, "3n+5"),
        (9, 1, "9n+1"),
        (11, 1, "11n+1"),
    ]
    
    print(f"\n{'映射':>10} | {'匹配率':>8} | {'反例':>40}")
    print("-" * 65)
    
    for a, b, name in cases:
        rate, mismatches = test_generalization(a, b, N=20000)
        mismatch_str = str(mismatches[:3]) if mismatches else "无"
        print(f"{name:>10} | {rate:7.2f}% | {mismatch_str[:40]}")

def deep_analysis_5n1():
    """深入分析 5n+1 映射的CRS结构"""
    print("\n" + "=" * 70)
    print("5n+1 映射的CRS深层分析")
    print("=" * 70)
    
    a, b = 5, 1
    
    # CRS长度分布
    from collections import Counter
    crs_counts = Counter()
    t1_counts = Counter()
    
    for n in range(1, 100000, 2):
        crs = crs_length(n, a, b)
        t1 = trailing_ones(n)
        crs_counts[crs] += 1
        t1_counts[t1] += 1
    
    total = sum(crs_counts.values())
    
    print(f"\nCRS长度分布 (5n+1):")
    print(f"{'k':>4} | {'CRS=k':>8} | {'P(CRS=k)':>10} | {'1/2^k':>10} | {'trailing=k':>10}")
    print("-" * 55)
    for k in range(1, 12):
        crs_p = crs_counts.get(k, 0) / total
        t1_p = t1_counts.get(k, 0) / total
        theory = 1 / (2**k)
        print(f"{k:4d} | {crs_counts.get(k,0):8d} | {crs_p:10.6f} | {theory:10.6f} | {t1_counts.get(k,0):10d}")
    
    # CRS上升条件分析
    print(f"\n上升条件: T(n) > n ⟺ v2(5n+1) = ?")
    rise_v2 = Counter()
    fall_v2 = Counter()
    for n in range(1, 50000, 2):
        tn = T_gen(n, 5, 1)
        v = v2(5*n + 1)
        if tn > n:
            rise_v2[v] += 1
        else:
            fall_v2[v] += 1
    
    print("上升时 v2 分布:", dict(sorted(rise_v2.items())))
    print("下降时 v2 分布:", dict(sorted(fall_v2.items())))
    
    # T(n) > n 的精确条件
    print(f"\n上升条件: 5n+1 > n·2^v2 ⟺ v2 < log2(5+1/n) ≈ log2(5) ≈ 2.32")
    print(f"所以上升 ⟺ v2(5n+1) ≤ 2")
    
    # 验证
    rise_correct = 0
    total_check = 0
    for n in range(1, 50000, 2):
        tn = T_gen(n, 5, 1)
        v = v2(5*n + 1)
        total_check += 1
        if (tn > n) == (v <= 2):
            rise_correct += 1
    
    print(f"验证: rise ⟺ v2≤2: {rise_correct/total_check*100:.2f}%")

def general_theory():
    """一般理论分析"""
    print("\n" + "=" * 70)
    print("一般理论: CRS与trailing ones的关系")
    print("=" * 70)
    
    print("""
对于映射 T_{a}(n) = (an+1)/2^{v2(an+1)}:

上升条件: T(n) > n ⟺ v2(an+1) < log2(a+1/n) ≈ log2(a)

Collatz (a=3): 上升 ⟺ v2=1 ⟺ n≡3(mod 4) ⟺ trailing_ones ≥ 2
  上升概率 = 1/2

5n+1 (a=5): 上升 ⟺ v2∈{1,2} ⟺ ?
  log2(5) ≈ 2.32, 所以 v2=1或2时上升
  上升概率 = 1/2 + 1/4 = 3/4 (更频繁上升!)
  这就解释了5n+1映射通常发散

7n+1 (a=7): 上升 ⟺ v2∈{1,2} ⟺ ?
  log2(7) ≈ 2.81, 所以 v2=1或2时上升
  上升概率 = 3/4 (同5n+1)

一般地, 对于 a:
  上升概率 ≈ 1 - 1/2^{floor(log2(a))}
  
  a=3: P(rise) = 1/2, E[rise per step] = log2(3) - 2 ≈ -0.415 (收敛)
  a=5: P(rise) = 3/4, E[rise per step] = log2(5) - 8/3 ≈ -0.345 (边界)
  a=7: P(rise) = 3/4, E[rise per step] = log2(7) - 8/3 ≈ +0.141 (发散!)

所以CRS=trailing_ones 是Collatz (a=3)的特殊性质：
因为上升条件恰好对应v2=1，而v2(3n+1)=1等价于n≡3(mod4)。
对于a>3，上升条件涉及多个v2值，与trailing_ones的关系更复杂。
""")

    # 验证预期漂移
    print("验证不同a的漂移率:")
    for a in [3, 5, 7, 9, 11]:
        drifts = []
        import math
        for n in range(3, 100000, 2):
            tn = T_gen(n, a, 1)
            if tn > 0:
                drifts.append(math.log2(tn) - math.log2(n))
        
        mean_drift = sum(drifts) / len(drifts)
        converges = "收敛" if mean_drift < 0 else "发散"
        print(f"  a={a:2d}: E[drift] = {mean_drift:+.6f}  ({converges})")

if __name__ == "__main__":
    analyze_generalization()
    deep_analysis_5n1()
    general_theory()
