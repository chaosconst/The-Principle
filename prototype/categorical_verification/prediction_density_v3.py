#!/usr/bin/env python3
"""
预测密度 v3：修正版噪声鲁棒性测试
===================================

修正：噪声加在动力学过程中（过程噪声），而非观测中。
这更准确地模拟了"环境扰动对推理能力的影响"。

核心问题：当推理过程本身受到干扰时，哪个系统仍能保持预测能力？
"""

import numpy as np

# 可复现性：设置固定种子
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
from collections import Counter

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


# ========== Qubit with process noise ==========
def run_qubit(n_steps, noise_level):
    """噪声加在Hadamard后的状态上（模拟退相干）"""
    state = np.array([1.0, 0.0])
    H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    states = []
    ops_per_step = 10
    
    for _ in range(n_steps):
        p0 = abs(state[0])**2
        disc = int(p0 * 64) % 64  # 更细的离散化
        states.append(disc)
        
        # Born测量
        result = 0 if np.random.random() < p0 else 1
        collapsed = np.array([1.0, 0.0]) if result == 0 else np.array([0.0, 1.0])
        
        # Hadamard演化
        state = H @ collapsed
        
        # 过程噪声：在Bloch球上加微扰
        if noise_level > 0:
            angle_noise = np.random.normal(0, noise_level * 0.1)
            cos_n, sin_n = np.cos(angle_noise), np.sin(angle_noise)
            rotation = np.array([[cos_n, -sin_n], [sin_n, cos_n]])
            state = rotation @ state
            # 重新归一化
            norm = np.sqrt(abs(state[0])**2 + abs(state[1])**2)
            if norm > 0:
                state = state / norm
    
    s_t, s_t1 = states[:-1], states[1:]
    mi = mutual_information(s_t, s_t1)
    return mi, ops_per_step


# ========== CA with process noise ==========
def run_ca(n_steps, noise_level, width=32):
    """噪声 = 每步有概率翻转某些cell"""
    rule = 110
    state = np.zeros(width, dtype=int)
    state[width//2] = 1
    states = []
    ops_per_step = width * 3
    flip_prob = min(noise_level * 0.02, 0.5)  # 噪声强度映射到翻转概率
    
    for _ in range(n_steps):
        density = sum(state) / width
        max_run = 0
        cr = 0
        for b in state:
            if b == 1:
                cr += 1
                max_run = max(max_run, cr)
            else:
                cr = 0
        disc = (int(density * 32) % 32, int(max_run/width * 16) % 16)
        states.append(disc)
        
        # Rule 110 演化
        new_state = np.zeros(width, dtype=int)
        for i in range(width):
            idx = (state[(i-1)%width] << 2) | (state[i] << 1) | state[(i+1)%width]
            new_state[i] = (rule >> idx) & 1
        
        # 过程噪声：随机翻转
        if noise_level > 0:
            for i in range(width):
                if np.random.random() < flip_prob:
                    new_state[i] = 1 - new_state[i]
        
        state = new_state
    
    s_t, s_t1 = states[:-1], states[1:]
    mi = mutual_information(s_t, s_t1)
    return mi, ops_per_step


# ========== Self-Referential with process noise ==========
def run_selfref(n_steps, noise_level):
    """噪声加在推理过程中（模拟认知噪声）"""
    value, hist_hash = 42, 0
    states = []
    ops_per_step = 11
    
    for _ in range(n_steps):
        disc = (value % 32, hist_hash % 32)
        states.append(disc)
        
        # 推理过程
        combined = (value * 7 + hist_hash * 13) % 256
        behavior = (combined ^ (combined >> 3) ^ (combined << 2)) % 256
        
        # 过程噪声：在推理结果上加扰动
        if noise_level > 0:
            noise = int(np.random.normal(0, noise_level * 2)) % 256
            behavior = (behavior + noise) % 256
        
        new_hash = ((hist_hash * 31) + behavior + value) % 256
        value, hist_hash = behavior, new_hash
    
    s_t, s_t1 = states[:-1], states[1:]
    mi = mutual_information(s_t, s_t1)
    return mi, ops_per_step


# ========== 主实验 ==========
def main():
    N = 50000
    noise_levels = [0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    
    print("=" * 80)
    print("预测密度 ρ — 过程噪声鲁棒性测试 (v3)")
    print(f"N = {N} steps | 噪声加在动力学过程中，非观测中")
    print("=" * 80)
    print()
    
    print(f"{'σ':>5s} | {'ρ_Qubit':>12s} | {'ρ_CA-32':>12s} | {'ρ_SelfRef':>12s} | {'Q<CA':>5s} | {'CA<SR':>5s} | {'All':>4s}")
    print("-" * 80)
    
    rho_data = {'qubit': [], 'ca': [], 'sr': []}
    
    for nl in noise_levels:
        # 多次运行取平均（减少随机波动）
        rhos_q, rhos_ca, rhos_sr = [], [], []
        n_runs = 3
        for _ in range(n_runs):
            mi_q, c_q = run_qubit(N, nl)
            mi_ca, c_ca = run_ca(N, nl, width=32)
            mi_sr, c_sr = run_selfref(N, nl)
            rhos_q.append(mi_q / c_q)
            rhos_ca.append(mi_ca / c_ca)
            rhos_sr.append(mi_sr / c_sr)
        
        rho_q = np.mean(rhos_q)
        rho_ca = np.mean(rhos_ca)
        rho_sr = np.mean(rhos_sr)
        
        rho_data['qubit'].append(rho_q)
        rho_data['ca'].append(rho_ca)
        rho_data['sr'].append(rho_sr)
        
        q_lt_ca = "✅" if rho_q < rho_ca else "❌"
        ca_lt_sr = "✅" if rho_ca < rho_sr else "❌"
        all_ok = "✅" if rho_q < rho_ca < rho_sr else "❌"
        
        print(f"{nl:5.1f} | {rho_q:12.6f} | {rho_ca:12.6f} | {rho_sr:12.6f} | {q_lt_ca} | {ca_lt_sr} | {all_ok}")
    
    print()
    
    # 衰减分析（相对于baseline）
    print("=" * 80)
    print("归一化衰减：ρ(σ) / ρ(0)")
    print("=" * 80)
    
    for nl_idx, nl in enumerate(noise_levels):
        r_q = rho_data['qubit'][nl_idx] / max(rho_data['qubit'][0], 1e-12)
        r_ca = rho_data['ca'][nl_idx] / max(rho_data['ca'][0], 1e-12)
        r_sr = rho_data['sr'][nl_idx] / max(rho_data['sr'][0], 1e-12)
        print(f"  σ={nl:5.1f}: Qubit={r_q:8.3f}, CA={r_ca:8.3f}, SelfRef={r_sr:8.3f}")
    
    print()
    print("=" * 80)
    print("解释")
    print("=" * 80)
    print("""
    过程噪声直接干扰推理过程本身，这是比观测噪声更本质的测试。
    
    如果自指系统的ρ在高噪声下仍然最高，说明：
    1. 记忆机制（历史编码）提供了对噪声的内在鲁棒性
    2. 自指不仅增加了预测力，还增加了预测的稳定性
    3. 这与生物系统的"稳态维持"能力类似
    
    存在光谱的层级不仅是ρ的绝对值排序，
    更是ρ对扰动的鲁棒性排序。
    """)

if __name__ == "__main__":
    main()
