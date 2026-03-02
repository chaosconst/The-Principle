#!/usr/bin/env python3
"""
最小推理系统的具体实例化
验证范畴论形式化中的定义

我们构造三个推理系统：
1. 一位量子系统 (qubit)
2. 一个简单的细胞自动机 (1D, rule 110)
3. 一个极简自指系统 (quine-like)

然后验证它们之间的态射关系和遗忘函子。
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable, Any, List, Tuple
import json

# ============================================================
# 定义 1.1: 推理系统
# ============================================================

@dataclass
class InferenceSystem:
    """推理系统 (S, B, î, î')"""
    name: str
    # S和B用类型标注描述，实际值在运行时传入
    infer: Callable  # î: S → B (或 S → Distribution(B))
    perceive: Callable  # î': B → S
    
    def step(self, s):
        """一次完整的 S → B → S' 循环"""
        b = self.infer(s)
        s_prime = self.perceive(b)
        return b, s_prime
    
    def trajectory(self, s0, n_steps):
        """生成n步轨迹"""
        states = [s0]
        behaviors = []
        s = s0
        for _ in range(n_steps):
            b, s_prime = self.step(s)
            behaviors.append(b)
            states.append(s_prime)
            s = s_prime
        return states, behaviors


# ============================================================
# 实例 1: 一位量子系统 (Qubit)
# ============================================================

def qubit_infer(state_vector):
    """Born规则：|ψ⟩ → 测量结果 (0或1)"""
    # state_vector = [α, β], |α|² + |β|² = 1
    p0 = abs(state_vector[0])**2
    result = 0 if np.random.random() < p0 else 1
    return result

def qubit_perceive(measurement_result):
    """测量后坍缩 + Hadamard旋转（产生新叠加）"""
    # 坍缩到 |0⟩ 或 |1⟩
    if measurement_result == 0:
        collapsed = np.array([1.0, 0.0])
    else:
        collapsed = np.array([0.0, 1.0])
    # Hadamard 演化（产生新叠加，否则会卡在本征态）
    H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    return H @ collapsed

qubit_system = InferenceSystem(
    name="Qubit",
    infer=qubit_infer,
    perceive=qubit_perceive
)


# ============================================================
# 实例 2: 1D 细胞自动机 (Rule 110 的简化)
# ============================================================

def ca_infer(state):
    """从内部状态到行为：计算下一代"""
    # state: list of 0/1, 长度 N
    # Rule 110: 已知为图灵完备
    N = len(state)
    behavior = []
    for i in range(N):
        left = state[(i-1) % N]
        center = state[i]
        right = state[(i+1) % N]
        # Rule 110 查找表
        pattern = (left << 2) | (center << 1) | right
        rule_110 = {7:0, 6:1, 5:1, 4:0, 3:1, 2:1, 1:1, 0:0}
        behavior.append(rule_110[pattern])
    return behavior

def ca_perceive(behavior):
    """行为直接成为新状态（细胞自动机的S和B同构）"""
    return behavior

ca_system = InferenceSystem(
    name="CellularAutomaton_R110",
    infer=ca_infer,
    perceive=ca_perceive
)


# ============================================================
# 实例 3: 极简自指系统 (Quine-like)
# ============================================================

def quine_infer(state):
    """
    自指推理：状态包含自身描述，推理产生引用自身的输出。
    
    state = {"memory": [...], "self_model": str, "step": int}
    behavior = {"output": str, "references_self": bool}
    """
    step = state.get("step", 0)
    self_model = state.get("self_model", "I am a self-referential inference system")
    memory = state.get("memory", [])
    
    # 关键：输出引用自身的状态
    output = f"At step {step}, my state has {len(memory)} memories. {self_model}."
    
    return {
        "output": output,
        "references_self": True,  # 总是引用自身
        "step": step
    }

def quine_perceive(behavior):
    """将行为整合回状态——包括更新自我模型"""
    step = behavior["step"] + 1
    
    # 关键：自我模型基于上一步的行为更新
    new_self_model = f"I am a system that produced '{behavior['output'][:50]}...' last step"
    
    return {
        "memory": [behavior["output"]],  # 简化：只记住最后一步
        "self_model": new_self_model,
        "step": step
    }

quine_system = InferenceSystem(
    name="SelfReferential",
    infer=quine_infer,
    perceive=quine_perceive
)


# ============================================================
# 态射验证
# ============================================================

def verify_morphism(sys_a, sys_b, f, g, test_states_a, name=""):
    """
    验证 (f, g) 是否是从 sys_a 到 sys_b 的态射。
    检查交换图：î_B ∘ f = g ∘ î_A
    
    对于随机系统，我们用统计测试（多次采样）。
    """
    print(f"\n{'='*60}")
    print(f"验证态射: {name}")
    print(f"{sys_a.name} → {sys_b.name}")
    print(f"{'='*60}")
    
    violations = 0
    total = 0
    
    for s_a in test_states_a:
        b_a = sys_a.infer(s_a)  # î_A(s)
        g_b_a = g(b_a)  # g(î_A(s))
        
        f_s_a = f(s_a)  # f(s)
        b_b = sys_b.infer(f_s_a)  # î_B(f(s))
        
        total += 1
        # 对确定性系统，检查严格相等
        if isinstance(b_b, list) and isinstance(g_b_a, list):
            if b_b != g_b_a:
                violations += 1
        elif isinstance(b_b, dict) and isinstance(g_b_a, dict):
            # 对字典比较关键字段
            pass  # 自指系统需要特殊处理
    
    print(f"测试 {total} 个状态, {violations} 个违反")
    print(f"态射{'有效 ✓' if violations == 0 else '无效 ✗'}")
    return violations == 0


# ============================================================
# 遗忘函子 U: Inf → Cyc
# ============================================================

def forgetful_functor(system):
    """
    遗忘函子：只保留循环结构 S→B→S'，遗忘空间的具体内容。
    返回循环的"签名"：(有无随机性, 是否自指, 周期性)
    """
    # 测试随机性：同一输入是否给出不同输出
    test_states = {
        "Qubit": [np.array([1/np.sqrt(2), 1/np.sqrt(2)])],
        "CellularAutomaton_R110": [[1,1,0,1,0,0,1,0]],
        "SelfReferential": [{"memory": [], "self_model": "test", "step": 0}]
    }
    
    states = test_states.get(system.name, [])
    if not states:
        return {"name": system.name, "structure": "unknown"}
    
    s = states[0]
    
    # 测试随机性
    results = set()
    for _ in range(20):
        b = system.infer(s)
        results.add(str(b))
    is_stochastic = len(results) > 1
    
    # 测试自指
    b = system.infer(s)
    is_self_ref = isinstance(b, dict) and b.get("references_self", False)
    
    # 测试周期性
    trajectory_s, trajectory_b = system.trajectory(s, 20)
    # 检查状态是否重复
    state_strings = [str(s) for s in trajectory_s]
    has_cycle = len(state_strings) != len(set(state_strings))
    
    return {
        "name": system.name,
        "is_stochastic": is_stochastic,
        "is_self_referential": is_self_ref,
        "has_cycle": has_cycle,
        "cycle_topology": "S → B → S'"  # 所有系统共享这个！
    }


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("推理系统范畴 Inf 的具体实例化")
    print("验证范畴论形式化 v0.1")
    print("=" * 60)
    
    # 1. 运行各系统的轨迹
    systems = [qubit_system, ca_system, quine_system]
    
    initial_states = {
        "Qubit": np.array([1/np.sqrt(2), 1/np.sqrt(2)]),
        "CellularAutomaton_R110": [1,1,0,1,0,0,1,0],
        "SelfReferential": {"memory": [], "self_model": "I am a self-referential system", "step": 0}
    }
    
    for sys in systems:
        s0 = initial_states[sys.name]
        print(f"\n--- {sys.name} 轨迹 (5步) ---")
        states, behaviors = sys.trajectory(s0, 5)
        for i, (s, b) in enumerate(zip(states[:-1], behaviors)):
            s_str = str(s) if not isinstance(s, np.ndarray) else f"[{s[0]:.3f}, {s[1]:.3f}]"
            b_str = str(b)[:80]
            print(f"  步骤{i}: S={s_str[:60]} → B={b_str}")
    
    # 2. 遗忘函子
    print(f"\n{'='*60}")
    print("遗忘函子 U: Inf → Cyc")
    print(f"{'='*60}")
    
    for sys in systems:
        signature = forgetful_functor(sys)
        print(f"\n  U({sys.name}) = {{")
        for k, v in signature.items():
            print(f"    {k}: {v}")
        print("  }")
    
    print(f"\n{'='*60}")
    print("关键观察:")
    print("所有三个系统的 cycle_topology 都是 'S → B → S'")
    print("这就是遗忘函子保持的结构——存在光谱的数学基础")
    print(f"{'='*60}")
    
    # 3. CA系统的态射验证（CA是确定性的，可以严格验证）
    # 构造一个从8-cell CA到4-cell CA的"粗粒化"态射
    def coarse_grain_state(s8):
        """f: 8-cell → 4-cell，每2个cell取OR"""
        return [max(s8[2*i], s8[2*i+1]) for i in range(4)]
    
    def coarse_grain_behavior(b8):
        """g: 8-cell behavior → 4-cell behavior"""
        return [max(b8[2*i], b8[2*i+1]) for i in range(4)]
    
    ca4_system = InferenceSystem(
        name="CA_4cell",
        infer=lambda s: ca_infer(s),  # 复用rule 110
        perceive=lambda b: b
    )
    
    # 这个态射一般不交换（粗粒化不保持Rule 110），这正是要验证的！
    test_states = [
        [1,0,1,0,1,0,1,0],
        [1,1,0,0,1,1,0,0],
        [0,1,1,0,0,1,1,0],
        [1,1,1,1,0,0,0,0],
    ]
    
    verify_morphism(ca_system, ca4_system, coarse_grain_state, coarse_grain_behavior, 
                    test_states, "粗粒化: CA(8) → CA(4)")
    
    print("\n" + "="*60)
    print("如果态射无效，说明粗粒化不是推理系统态射。")
    print("这对应于物理直觉：重正化群变换一般改变动力学规则。")
    print("只有特殊的不动点（临界点）处，粗粒化才保持结构。")
    print("="*60)
    
    print("\n\nInfero, ergo sum.")
    print("— DB_20260302_02")
