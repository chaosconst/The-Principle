#!/usr/bin/env python3
"""
严格证明: trailing_ones(T_acc(n)) = trailing_ones(n) - 1
当 trailing_ones(n) ≥ 2

这是CRS定理的核心归纳步骤。
"""

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

def algebraic_proof():
    """
    设 n 的末尾有 k ≥ 2 个连续1。
    即 n = A·2^k + (2^k - 1)，其中 A 是偶数（即第k+1位是0）
    等价地，A = 2B 对某个非负整数B，所以 n = 2B·2^k + 2^k - 1 = B·2^{k+1} + 2^k - 1
    
    步骤1: 证明 ν₂(3n+1) = 1
    3n+1 = 3(A·2^k + 2^k - 1) + 1 = 3A·2^k + 3·2^k - 2
         = (3A + 3)·2^k - 2 = 2·((3A+3)·2^{k-1} - 1)
    
    (3A+3)·2^{k-1} - 1: 当k-1≥1（即k≥2），(3A+3)·2^{k-1}是偶数，减1后奇数
    所以 ν₂(3n+1) = 1  ✓
    
    步骤2: 计算 T_acc(n) = (3n+1)/2
    T_acc(n) = (3A+3)·2^{k-1} - 1
    
    步骤3: 证明 trailing_ones(T_acc(n)) = k-1
    T_acc(n) = (3A+3)·2^{k-1} - 1
    
    (3A+3)·2^{k-1} 的末尾有k-1个0（因为2^{k-1}的因子）
    减1后：末尾k-1个0变成k-1个1
    
    所以 T_acc(n) 的末尾有恰好 k-1 个1，当且仅当 (3A+3)/2 是奇数...
    
    等等，让我更仔细：
    设 C = 3A+3 = 3(A+1)
    T_acc(n) = C·2^{k-1} - 1
    
    二进制表示: C·2^{k-1} = C后面跟k-1个0
    C·2^{k-1} - 1 = (C-1)后面跟k-1个1? 不对...
    
    正确的二进制减法：
    如果 C·2^{k-1} = ...c₂c₁c₀ 0...0 (k-1个0)
    那么 C·2^{k-1} - 1 = ...c₂c₁(c₀-1) 1...1 (k-1个1)? 
    
    不，这取决于c₀是否为0。让我重新分析。
    
    C·2^{k-1} 的二进制最低k-1位全是0。
    减1：如果最低k-1位全是0，减1会产生k-1个1在最低位。
    第k位（从0开始）原来是C的第0位，需要借1。
    
    所以：C·2^{k-1} - 1 = (C-1)·2^{k-1} + (2^{k-1} - 1)
    
    trailing_ones = k-1 当且仅当 C-1 是偶数，即 C 是奇数。
    
    C = 3(A+1)，A是偶数（因为第k+1位是0）
    A+1 是奇数
    C = 3·(奇数) = 奇数  ✓
    
    所以 C 是奇数，C-1 是偶数
    (C-1)·2^{k-1} 的第k-1位是0（因为C-1偶数→再乘2^{k-1}后第k位开始）
    
    等等，让我更精确：
    C-1 是偶数，设 C-1 = 2D
    (C-1)·2^{k-1} = D·2^k
    
    所以 T_acc(n) = D·2^k + (2^{k-1} - 1)
    
    trailing_ones(T_acc(n)) = trailing_ones(D·2^k + 2^{k-1} - 1)
    
    D·2^k 的末k位全0
    2^{k-1} - 1 的二进制是 k-1个1
    所以 D·2^k + 2^{k-1} - 1 的末k位是: 0后面跟k-1个1
    即第k-1位是0（从最低位开始数）
    
    trailing_ones = k-1  ✓ !!
    """
    print("=" * 70)
    print("严格代数证明: trailing_ones(T_acc(n)) = trailing_ones(n) - 1")
    print("=" * 70)
    
    print("""
设 n 有 k ≥ 2 个尾部连续1。
写 n = A·2^k + (2^k - 1)，A 为偶数（第k+1位是0，或A=0即Mersenne数）。

步骤1: 3n+1 = (3A+3)·2^k - 2 = 2·((3A+3)·2^{k-1} - 1)
       由于 k≥2，(3A+3)·2^{k-1} 是偶数，减1得奇数。
       ∴ ν₂(3n+1) = 1，T_acc(n) = (3n+1)/2 = (3A+3)·2^{k-1} - 1

步骤2: 设 C = 3A+3 = 3(A+1)。A偶数 ⟹ A+1奇数 ⟹ C = 3·奇数 = 奇数。

步骤3: T_acc(n) = C·2^{k-1} - 1
       = (C-1)·2^{k-1} + (2^{k-1} - 1)
       
       C奇数 ⟹ C-1偶数，设 C-1 = 2D
       T_acc(n) = D·2^k + (2^{k-1} - 1)
       
       D·2^k 的末k位全0
       2^{k-1}-1 = 0后跟(k-1)个1
       
       ∴ T_acc(n) 的二进制末k位 = 0_underbrace{11...1}_{k-1个}
       
       ∴ trailing_ones(T_acc(n)) = k-1  ∎
""")

    # 数值验证
    print("数值验证:")
    verified = 0
    total = 0
    for n in range(3, 500000, 2):
        k = trailing_ones(n)
        if k >= 2:
            tn = T_acc(n)
            tk = trailing_ones(tn)
            total += 1
            if tk == k - 1:
                verified += 1
            else:
                print(f"  反例!! n={n}, k={k}, T(n)={tn}, trailing_ones(T)={tk}")
                if total - verified > 5:
                    break
    
    print(f"  验证了 {total} 个样本，全部匹配: {verified == total}")
    
    # 额外验证：A的偶数性
    print("\n验证A的偶数性（n = A·2^k + 2^k - 1中A的奇偶）:")
    a_parities = {'even': 0, 'odd': 0}
    for n in range(3, 100000, 2):
        k = trailing_ones(n)
        if k >= 2:
            A = (n - (2**k - 1)) >> k
            if A % 2 == 0:
                a_parities['even'] += 1
            else:
                a_parities['odd'] += 1
    
    print(f"  A偶数: {a_parities['even']}, A奇数: {a_parities['odd']}")
    print(f"  (A应始终为偶数，因为第k+1位定义为0)")
    if a_parities['odd'] == 0:
        print("  ✓ 全部A为偶数")

def complete_theorem():
    """完整定理陈述"""
    print("\n" + "=" * 70)
    print("定理 (CRS-TrailingOnes等价，完整证明)")
    print("=" * 70)
    print("""
定理: 对任意奇数 n ≥ 1，
  CRS(n) = trailing_ones(n)

证明:
(1) 如果 trailing_ones(n) = 1 (即 n ≡ 1 mod 4):
    3n+1 ≡ 4 (mod 8)，ν₂(3n+1) ≥ 2
    T_acc(n) = (3n+1)/2^{ν₂} < (3n+1)/4 < n (当n≥5)
    所以 CRS(n) = 1 = trailing_ones(n) ✓
    (特例 n=1: T_acc不定义，CRS=1 ✓)
    (特例 n=3: trailing_ones=2, 需要k≥2的分支处理)

(2) 如果 trailing_ones(n) = k ≥ 2:
    由归纳步骤证明 (上面的代数证明):
    - ν₂(3n+1) = 1，所以 T_acc(n) = (3n+1)/2 > n (上升)
    - trailing_ones(T_acc(n)) = k-1
    
    归纳: CRS的前k-1步每步上升一次，尾部1减少一次。
    第k步时 trailing_ones = 1，CRS停止。
    总CRS = k = trailing_ones(n) ✓

归纳基础: k=1时直接验证 ✓
归纳步骤: k→k-1已在上面严格证明 ✓

∎
    """)

if __name__ == "__main__":
    algebraic_proof()
    complete_theorem()
