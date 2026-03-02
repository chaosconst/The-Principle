#!/usr/bin/env python3
"""
预测密度 ρ 的可计算版本
========================

定义：ρ = I(S_t; S_{t+1}) / C(î)

其中：
- I(S_t; S_{t+1}) = 互信息，衡量当前状态对下一状态的预测能力
- C(î) = 推理操作的计算成本（以基本操作数衡量）

我们在三个推理系统上测量 ρ，验证存在光谱的定量预测：
    ρ_qubit < ρ_CA < ρ_self_ref
"""

import numpy as np
from collections import Counter
import time
import sys

# ============================================================
# 工具函数：信息论计算
# ============================================================

def entropy(sequence):
    """计算离散序列的Shannon熵 H(X)"""
    counts = Counter(sequence)
    total = len(sequence)
    h = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            h -= p * np.log2(p)
    return h

def joint_entropy(seq_x, seq_y):
    """计算联合熵 H(X,Y)"""
    pairs = list(zip(seq_x, seq_y))
    return entropy(pairs)

def mutual_information(seq_x, seq_y):
    """计算互信息 I(X;Y) = H(X) + H(Y) - H(X,Y)"""
    hx = entropy(seq_x)
    hy = entropy(seq_y)
    hxy = joint_entropy(seq_x, seq_y)
    return hx + hy - hxy

def discretize(value, bins=16):
    """将连续值离散化到bins个桶"""
    if isinstance(value, (list, np.ndarray)):
        # 多维值：分别离散化后组合
        return tuple(int(v * bins) % bins for v in value)
    return int(value * bins) % bins

# ============================================================
# 系统 1: Qubit
# ============================================================

class QubitSystem:
    """一位量子系统：Hadamard + Born测量"""
    
    def __init__(self):
        self.name = "Qubit"
        self.op_count = 0  # 操作计数器
    
    def step(self, state):
        """state = [α, β] 复振幅"""
        self.op_count = 0
        
        # Born测量：2次乘法 + 1次比较
        p0 = abs(state[0])**2
        self.op_count += 3
        result = 0 if np.random.random() < p0 else 1
        
        # 坍缩
        if result == 0:
            collapsed = np.array([1.0, 0.0])
        else:
            collapsed = np.array([0.0, 1.0])
        self.op_count += 1
        
        # Hadamard演化：4次乘法 + 2次加法
        H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
        new_state = H @ collapsed
        self.op_count += 6
        
        return new_state, self.op_count
    
    def state_to_discrete(self, state):
        """将量子态离散化（用|α|²表示，因为全局相位不可观测）"""
        p0 = abs(state[0])**2
        return discretize(p0, bins=16)
    
    def run(self, n_steps=10000):
        state = np.array([1.0, 0.0])  # 初始 |0⟩
        states_discrete = []
        total_ops = 0
        
        for _ in range(n_steps):
            states_discrete.append(self.state_to_discrete(state))
            state, ops = self.step(state)
            total_ops += ops
        states_discrete.append(self.state_to_discrete(state))
        
        # 计算互信息 I(S_t; S_{t+1})
        s_t = states_discrete[:-1]
        s_t1 = states_discrete[1:]
        mi = mutual_information(s_t, s_t1)
        
        # 计算平均每步成本
        avg_cost = total_ops / n_steps
        
        # 预测密度
        rho = mi / avg_cost if avg_cost > 0 else 0
        
        return {
            'name': self.name,
            'mutual_information': mi,
            'avg_cost': avg_cost,
            'prediction_density': rho,
            'state_entropy': entropy(s_t),
            'n_unique_states': len(set(s_t))
        }


# ============================================================
# 系统 2: 1D 细胞自动机 (Rule 110)
# ============================================================

class CellularAutomaton:
    """1D细胞自动机，Rule 110"""
    
    def __init__(self, width=32):
        self.name = f"CA-Rule110-w{width}"
        self.width = width
        self.rule = 110  # 01101110 in binary
        self.op_count = 0
    
    def _apply_rule(self, left, center, right):
        """应用rule 110到三个邻居"""
        self.op_count += 3  # 3次位操作
        index = (left << 2) | (center << 1) | right
        return (self.rule >> index) & 1
    
    def step(self, state):
        """一步CA演化"""
        self.op_count = 0
        n = len(state)
        new_state = np.zeros(n, dtype=int)
        for i in range(n):
            left = state[(i-1) % n]
            center = state[i]
            right = state[(i+1) % n]
            new_state[i] = self._apply_rule(left, center, right)
        return new_state, self.op_count
    
    def state_to_discrete(self, state):
        """将CA状态映射到离散值"""
        # 用密度（1的比例）+ 边界特征 来描述
        density = sum(state) / len(state)
        # 计算块状特征：连续1的最长run
        max_run = 0
        current_run = 0
        for bit in state:
            if bit == 1:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        max_run_norm = max_run / len(state)
        
        return (discretize(density, 16), discretize(max_run_norm, 8))
    
    def run(self, n_steps=10000):
        # 初始状态：中心一个1
        state = np.zeros(self.width, dtype=int)
        state[self.width // 2] = 1
        
        states_discrete = []
        total_ops = 0
        
        for _ in range(n_steps):
            states_discrete.append(self.state_to_discrete(state))
            state, ops = self.step(state)
            total_ops += ops
        states_discrete.append(self.state_to_discrete(state))
        
        s_t = states_discrete[:-1]
        s_t1 = states_discrete[1:]
        mi = mutual_information(s_t, s_t1)
        avg_cost = total_ops / n_steps
        rho = mi / avg_cost if avg_cost > 0 else 0
        
        return {
            'name': self.name,
            'mutual_information': mi,
            'avg_cost': avg_cost,
            'prediction_density': rho,
            'state_entropy': entropy(s_t),
            'n_unique_states': len(set(s_t))
        }


# ============================================================
# 系统 3: 自指推理系统
# ============================================================

class SelfReferentialSystem:
    """
    极简自指系统：状态包含对自身历史的摘要
    
    关键区别：这个系统的î不仅处理输入，还引用自己的处理历史。
    这使得 S_{t+1} 与整个历史相关，而不仅仅是 S_t。
    
    但我们测量的是 I(S_t; S_{t+1})，所以如果自指使得
    S_t 已经编码了历史信息，那么 I(S_t; S_{t+1}) 会更高。
    """
    
    def __init__(self, memory_depth=4):
        self.name = f"SelfRef-d{memory_depth}"
        self.memory_depth = memory_depth
        self.op_count = 0
    
    def step(self, state):
        """
        state = (current_value, history_hash)
        推理 = 基于当前值和历史哈希生成新值
        感知 = 更新历史哈希（自指！）
        """
        self.op_count = 0
        
        current_value, history_hash = state
        
        # î: 推理 — 结合当前值和历史来决策
        # 这里的关键是history_hash让系统能"记住"模式
        combined = (current_value * 7 + history_hash * 13) % 256
        self.op_count += 3  # 2次乘法 + 1次模
        
        # 非线性变换（模拟复杂推理）
        behavior = (combined ^ (combined >> 3) ^ (combined << 2)) % 256
        self.op_count += 4  # 位操作
        
        # î': 感知 — 更新历史哈希（这是自指的核心）
        # 新的历史哈希编码了旧哈希 + 新行为
        new_hash = ((history_hash * 31) + behavior + current_value) % 256
        self.op_count += 3
        
        # 新的当前值来自行为
        new_value = behavior
        self.op_count += 1  # 赋值
        
        new_state = (new_value, new_hash)
        return new_state, self.op_count
    
    def state_to_discrete(self, state):
        """状态本身已经是离散的"""
        return state  # (value, hash) 的元组
    
    def run(self, n_steps=10000):
        # 初始状态
        state = (42, 0)  # 任意初始值，空历史
        
        states_discrete = []
        total_ops = 0
        
        for _ in range(n_steps):
            states_discrete.append(self.state_to_discrete(state))
            state, ops = self.step(state)
            total_ops += ops
        states_discrete.append(self.state_to_discrete(state))
        
        s_t = states_discrete[:-1]
        s_t1 = states_discrete[1:]
        mi = mutual_information(s_t, s_t1)
        avg_cost = total_ops / n_steps
        rho = mi / avg_cost if avg_cost > 0 else 0
        
        return {
            'name': self.name,
            'mutual_information': mi,
            'avg_cost': avg_cost,
            'prediction_density': rho,
            'state_entropy': entropy(s_t),
            'n_unique_states': len(set(s_t))
        }


# ============================================================
# 系统 4: 增强自指系统（更深的记忆）
# ============================================================

class DeepSelfReferentialSystem:
    """
    深度自指系统：维护显式的历史窗口
    
    与浅层自指不同，这个系统保留最近N步的完整状态，
    用它来做更精确的预测。模拟了真实认知系统的工作记忆。
    """
    
    def __init__(self, memory_depth=8):
        self.name = f"DeepSelfRef-d{memory_depth}"
        self.memory_depth = memory_depth
        self.op_count = 0
    
    def step(self, state):
        """
        state = (current_value, history_tuple)
        history_tuple 保存最近 memory_depth 步的值
        """
        self.op_count = 0
        
        current_value, history = state
        
        # î: 用历史模式来推理
        # 计算历史的加权和（最近的权重更大）
        weighted_sum = 0
        for i, h in enumerate(history):
            weighted_sum += h * (i + 1)
            self.op_count += 2  # 乘法 + 加法
        
        # 结合当前值和历史模式
        combined = (current_value * 11 + weighted_sum * 3) % 256
        self.op_count += 3
        
        # 非线性变换
        behavior = combined
        for _ in range(3):  # 多轮混合
            behavior = (behavior ^ (behavior >> 2) ^ (behavior << 3)) % 256
            self.op_count += 4
        
        # î': 感知 — 更新历史窗口（自指）
        new_history = history[1:] + (behavior,)  # 滑动窗口
        self.op_count += 1
        
        new_state = (behavior, new_history)
        return new_state, self.op_count
    
    def state_to_discrete(self, state):
        """使用(current, history_hash)作为离散状态"""
        current, history = state
        h = hash(history) % 256  # 压缩历史
        return (current, h)
    
    def run(self, n_steps=10000):
        # 初始：零历史
        initial_history = tuple([0] * self.memory_depth)
        state = (42, initial_history)
        
        states_discrete = []
        total_ops = 0
        
        for _ in range(n_steps):
            states_discrete.append(self.state_to_discrete(state))
            state, ops = self.step(state)
            total_ops += ops
        states_discrete.append(self.state_to_discrete(state))
        
        s_t = states_discrete[:-1]
        s_t1 = states_discrete[1:]
        mi = mutual_information(s_t, s_t1)
        avg_cost = total_ops / n_steps
        rho = mi / avg_cost if avg_cost > 0 else 0
        
        return {
            'name': self.name,
            'mutual_information': mi,
            'avg_cost': avg_cost,
            'prediction_density': rho,
            'state_entropy': entropy(s_t),
            'n_unique_states': len(set(s_t))
        }


# ============================================================
# 主实验
# ============================================================

def main():
    print("=" * 70)
    print("预测密度 ρ 的定量测量")
    print("验证存在光谱预测：ρ_qubit < ρ_CA < ρ_self_ref")
    print("=" * 70)
    print()
    
    N = 50000  # 足够大以获得稳定估计
    
    systems = [
        QubitSystem(),
        CellularAutomaton(width=16),
        CellularAutomaton(width=32),
        SelfReferentialSystem(memory_depth=4),
        DeepSelfReferentialSystem(memory_depth=4),
        DeepSelfReferentialSystem(memory_depth=8),
    ]
    
    results = []
    for sys in systems:
        print(f"运行 {sys.name}...")
        t0 = time.time()
        result = sys.run(n_steps=N)
        elapsed = time.time() - t0
        result['wall_time'] = elapsed
        results.append(result)
        
        print(f"  I(S_t;S_{{t+1}}) = {result['mutual_information']:.4f} bits")
        print(f"  平均成本 C(î)   = {result['avg_cost']:.1f} ops/step")
        print(f"  预测密度 ρ      = {result['prediction_density']:.6f} bits/op")
        print(f"  状态熵 H(S)     = {result['state_entropy']:.4f} bits")
        print(f"  独立状态数      = {result['n_unique_states']}")
        print(f"  耗时            = {elapsed:.2f}s")
        print()
    
    # 排序并分析
    print("=" * 70)
    print("按预测密度排序:")
    print("=" * 70)
    results.sort(key=lambda r: r['prediction_density'])
    
    for i, r in enumerate(results):
        rank = i + 1
        print(f"  #{rank} {r['name']:30s} ρ = {r['prediction_density']:.6f} bits/op | I = {r['mutual_information']:.4f} | C = {r['avg_cost']:.1f}")
    
    print()
    
    # 验证预测
    qubit_rho = [r for r in results if 'Qubit' in r['name']][0]['prediction_density']
    ca_rhos = [r['prediction_density'] for r in results if 'CA' in r['name']]
    sr_rhos = [r['prediction_density'] for r in results if 'SelfRef' in r['name'] or 'DeepSelfRef' in r['name']]
    
    max_ca = max(ca_rhos) if ca_rhos else 0
    min_sr = min(sr_rhos) if sr_rhos else 0
    
    print("=" * 70)
    print("存在光谱预测验证:")
    print("=" * 70)
    print(f"  ρ_qubit     = {qubit_rho:.6f}")
    print(f"  ρ_CA (max)  = {max_ca:.6f}")
    print(f"  ρ_self (min)= {min_sr:.6f}")
    print()
    
    if qubit_rho < max_ca < min_sr:
        print("  ✅ 预测 ρ_qubit < ρ_CA < ρ_self_ref 成立！")
        print("  存在光谱有了第一个定量证据。")
    elif qubit_rho < max_ca:
        print("  ⚠️ ρ_qubit < ρ_CA 成立，但 ρ_CA < ρ_self_ref 未确认")
        print("  部分验证。")
    else:
        print("  ❌ 预测未成立。需要调查原因。")
        print("  可能的原因：离散化粒度、系统参数、样本量等。")
    
    print()
    print("=" * 70)
    print("物理解释:")
    print("=" * 70)
    print("""
    预测密度 ρ 衡量的是系统每单位计算成本所能预测的信息量。
    
    • 量子系统 ρ 低：Born测量是概率性的，计算成本固定但预测力有限
    • 细胞自动机 ρ 中等：确定性规则使预测力高，但成本与宽度线性增长
    • 自指系统 ρ 高：历史记忆压缩了过去信息，使每单位成本的预测力更强
    
    存在光谱的方向 = ρ 增长的方向 = 进化的方向。
    生命之所以比无机物"更高级"，不是因为更复杂，
    而是因为它以更少的计算成本做出了更准确的预测。
    """)

if __name__ == "__main__":
    main()
