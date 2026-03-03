#!/usr/bin/env python3
"""
Mersenne CRS定理的严格证明
============================
定理: CRS(2^k - 1) = k 对所有 k ≥ 2 成立。

证明策略：
1. 证明CRS期间每步恰好是 n → (3n+1)/2
2. 追踪精确的代数表达式
3. 证明第k步时ν₂ > 1，CRS终止
"""
import sympy
from sympy import Symbol, simplify, factor, Mod, Integer
import math

def prove_crs_step_by_step():
    """
    用代数方法追踪 2^k-1 的CRS轨迹
    
    设 a₀ = 2^k - 1
    a₁ = (3a₀ + 1)/2 = (3·2^k - 2)/2 = 3·2^{k-1} - 1
    
    一般地，设 aⱼ 是CRS第j步的值。
    如果在CRS期间每步都是 ×3/2 (即ν₂=1)，则
    aⱼ = (3/2)^j · (2^k - 1) + 修正项
    
    让我精确追踪。
    """
    print("=" * 70)
    print("Mersenne CRS 代数追踪")
    print("=" * 70)
    
    # 对于一般的k，追踪CRS
    for k in [4, 6, 8]:
        print(f"\n--- k = {k}, a₀ = 2^{k} - 1 = {(1<<k)-1} ---")
        
        # 精确代数追踪
        a = (1 << k) - 1
        K = k  # 2的幂次
        
        for step in range(k + 2):
            # 3a + 1
            three_a_plus_1 = 3 * a + 1
            nu2 = 0
            temp = three_a_plus_1
            while temp % 2 == 0:
                nu2 += 1
                temp //= 2
            
            # 用2^k表示a
            # a = c * 2^k + d 的形式
            c = a >> k
            d = a & ((1 << k) - 1)
            
            print(f"  a_{step} = {a:>12d} = {c}·2^{k} + {d}")
            print(f"    3a+1 = {three_a_plus_1}, ν₂ = {nu2}")
            
            if nu2 > 1:
                print(f"    CRS终止于步{step} (ν₂ = {nu2} > 1)")
                break
            
            a = three_a_plus_1 // 2

def prove_algebraically():
    """
    代数证明：追踪CRS的精确递推关系
    
    关键递推：
    如果 aⱼ ≡ 3 (mod 4)，则 ν₂(3aⱼ+1) = 1，
    aⱼ₊₁ = (3aⱼ + 1) / 2
    
    设 aⱼ = 2^k · cⱼ + (2^k - 1) - rⱼ (某种分解)
    
    实际上更好的表示：
    a₀ = 2^k - 1
    a₁ = (3·2^k - 2) / 2 = 3·2^{k-1} - 1
    a₂ = (3(3·2^{k-1} - 1) + 1) / 2 = (9·2^{k-1} - 2) / 2 = 9·2^{k-2} - 1
    a₃ = (3(9·2^{k-2} - 1) + 1) / 2 = (27·2^{k-2} - 2) / 2 = 27·2^{k-3} - 1
    
    一般地: aⱼ = 3^j · 2^{k-j} - 1  对 0 ≤ j ≤ k-1
    """
    print("\n" + "=" * 70)
    print("代数证明: aⱼ = 3^j · 2^{k-j} - 1")
    print("=" * 70)
    
    print("\n假设: aⱼ = 3^j · 2^{k-j} - 1")
    print("验证 a₀: 3^0 · 2^k - 1 = 2^k - 1 ✓")
    print("\n递推验证:")
    print("  若 aⱼ = 3^j · 2^{k-j} - 1，则")
    print("  3aⱼ + 1 = 3^{j+1} · 2^{k-j} - 3 + 1 = 3^{j+1} · 2^{k-j} - 2")
    print("  = 2 · (3^{j+1} · 2^{k-j-1} - 1)")
    print("  所以 ν₂(3aⱼ+1) ≥ 1")
    print("  (3aⱼ+1)/2 = 3^{j+1} · 2^{k-j-1} - 1 = a_{j+1} ✓")
    
    print("\n关键: 何时 ν₂(3aⱼ+1) = 1 (CRS继续)?")
    print("  3aⱼ+1 = 3^{j+1} · 2^{k-j} - 2 = 2·(3^{j+1} · 2^{k-j-1} - 1)")
    print("  需要 3^{j+1} · 2^{k-j-1} - 1 是奇数")
    print("  即 3^{j+1} · 2^{k-j-1} 是偶数")
    print("  当 k-j-1 ≥ 1 时 (即 j ≤ k-2)，这成立")
    print("  所以对 j = 0, 1, ..., k-2，CRS继续")
    
    print("\n终止: 当 j = k-1 时：")
    print("  a_{k-1} = 3^{k-1} · 2^1 - 1 = 2·3^{k-1} - 1")
    print("  3·a_{k-1} + 1 = 3·(2·3^{k-1} - 1) + 1 = 2·3^k - 2 = 2(3^k - 1)")
    print("  ν₂(3·a_{k-1}+1) = 1 + ν₂(3^k - 1)")
    print("  由于 3^k - 1 是偶数 (3^k奇数)，ν₂(3^k-1) ≥ 1")
    print("  所以 ν₂ ≥ 2，CRS终止！")
    
    print("\n但等等——a_{k-1} 到 a_k 这一步还是上升的吗？")
    print("  a_k = (3·a_{k-1}+1) / 2^{ν₂}")
    print("  让我们检查...")
    
    # 验证
    print("\n数值验证:")
    print(f"{'k':>4} | {'a_{k-1}':>15} | {'3a+1':>15} | {'ν₂':>4} | {'a_k':>15} | {'上升?':>6}")
    print("-" * 70)
    for k in range(2, 20):
        a_km1 = 2 * (3 ** (k-1)) - 1
        three_a_1 = 3 * a_km1 + 1
        nu2 = 0
        temp = three_a_1
        while temp % 2 == 0:
            nu2 += 1
            temp //= 2
        a_k = three_a_1 >> nu2
        rises = "是" if a_k > a_km1 else "否"
        # 验证公式
        a_km1_check = (3 ** (k-1)) * 2 - 1
        assert a_km1 == a_km1_check
        if k <= 12:
            print(f"{k:4d} | {a_km1:15d} | {three_a_1:15d} | {nu2:4d} | {a_k:15d} | {rises:>6}")
    
    print("\n" + "=" * 70)
    print("完整定理陈述")
    print("=" * 70)
    print("""
定理 (Mersenne CRS): 
设 M_k = 2^k - 1 (k ≥ 2)。则：

(1) 加速Collatz映射下，M_k 的CRS轨迹为
    a_j = 3^j · 2^{k-j} - 1, 对 j = 0, 1, ..., k-1
    
(2) 对 0 ≤ j ≤ k-2, ν₂(3a_j+1) = 1 (CRS继续)

(3) 对 j = k-1, ν₂(3a_{k-1}+1) = 1 + ν₂(3^k - 1) ≥ 2 (CRS终止)

(4) CRS长度 = k (包含起始点)

(5) CRS的总增长因子 = a_{k-1}/a_0 = (2·3^{k-1}-1)/(2^k-1)
    ≈ (3/2)^{k-1} 当 k → ∞

证明:
(1) 归纳法。基础: a_0 = 3^0·2^k - 1 = 2^k - 1 = M_k ✓
    递推: 3a_j + 1 = 3^{j+1}·2^{k-j} - 2 = 2(3^{j+1}·2^{k-j-1} - 1)
    当 k-j-1 ≥ 1 (即 j ≤ k-2) 时，3^{j+1}·2^{k-j-1} 是偶数，
    所以 3^{j+1}·2^{k-j-1} - 1 是奇数，ν₂ = 1。
    a_{j+1} = (3a_j+1)/2 = 3^{j+1}·2^{k-j-1} - 1 ✓

(2) 直接由(1)的证明过程得出。

(3) 当 j = k-1: a_{k-1} = 2·3^{k-1} - 1
    3a_{k-1}+1 = 6·3^{k-1} - 2 = 2(3^k - 1)
    3^k ≡ 1 (mod 2) 始终成立，所以 3^k-1 ≡ 0 (mod 2)
    因此 ν₂(3a_{k-1}+1) = 1 + ν₂(3^k-1) ≥ 2 ∎

(4) CRS包含 a_0, a_1, ..., a_{k-1}，共k项。

(5) 直接计算。 ∎
""")

def analyze_v2_of_3k_minus_1():
    """
    进一步分析: ν₂(3^k - 1) 的行为
    这决定了Mersenne CRS终止后的"下降幅度"
    """
    print("=" * 70)
    print("ν₂(3^k - 1) 的深层结构")
    print("=" * 70)
    
    print(f"\n{'k':>4} | {'3^k-1':>15} | {'ν₂(3^k-1)':>10} | {'k mod 2':>8} | {'k mod 4':>8}")
    print("-" * 55)
    
    v2_vals = []
    for k in range(1, 30):
        val = 3**k - 1
        nu2 = 0
        temp = val
        while temp % 2 == 0:
            nu2 += 1
            temp //= 2
        v2_vals.append(nu2)
        if k <= 20:
            print(f"{k:4d} | {val:15d} | {nu2:10d} | {k%2:8d} | {k%4:8d}")
    
    print("\n观察: ν₂(3^k - 1) 的规律")
    print("k奇数: ν₂ = 1 (因为 3^k ≡ 3 mod 4)")
    print("k偶数: ν₂ ≥ 2")
    print("k≡0 mod 2 但 k≢0 mod 4: ν₂ = 2 (3^2=9≡1 mod 4, 3^2-1=8, ν₂=3?)")
    
    # 更精确的分析
    print("\n精确的2-adic赋值:")
    print("ν₂(3^1-1) = ν₂(2) = 1")
    print("ν₂(3^2-1) = ν₂(8) = 3")
    print("这是 lifting the exponent lemma (LTE) 的结果:")
    print("ν₂(3^k - 1) = ν₂(3-1) + ν₂(3+1) + ν₂(k) - 1 = 1 + 2 + ν₂(k) - 1 = 2 + ν₂(k)")
    print("（当k为偶数时）")
    print("ν₂(3^k - 1) = ν₂(3-1) = 1")
    print("（当k为奇数时）")
    
    print("\n验证 LTE 公式 (k偶数): ν₂(3^k-1) = 2 + ν₂(k)")
    for k in range(2, 30, 2):
        val = 3**k - 1
        nu2_actual = 0
        temp = val
        while temp % 2 == 0:
            nu2_actual += 1
            temp //= 2
        
        nu2_k = 0
        temp = k
        while temp % 2 == 0:
            nu2_k += 1
            temp //= 2
        
        nu2_predicted = 2 + nu2_k
        match = "✓" if nu2_actual == nu2_predicted else "✗"
        if k <= 20:
            print(f"  k={k:3d}: actual ν₂={nu2_actual}, predicted 2+ν₂({k})=2+{nu2_k}={nu2_predicted} {match}")

if __name__ == "__main__":
    prove_algebraically()
    print()
    analyze_v2_of_3k_minus_1()
