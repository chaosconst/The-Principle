## 7.5 Experiment 3b: Conditional Prediction Density

### The Counter Counterexample

Our original ρ_int = I(S_t; S_{t+1}) / C(Î) suffers from a fundamental flaw: a deterministic counter `state = (state+1) % N` achieves ρ_int = log₂(N)/2, higher than any genuine reasoning system. The counter is perfectly predictable but performs no inference about its environment.

### Definition

We propose **conditional prediction density**:

$$\rho_{cond} = \frac{I(S_{t+1}; E_t \mid S_t)}{C(\hat{I})}$$

This measures how much information about the environment input $E_t$ is captured in the state transition $S_t \to S_{t+1}$, normalized by computational cost. The conditioning on $S_t$ ensures we measure only *new* environmental information integrated at each step.

### Experimental Setup

Three systems operate in a patterned stochastic environment (period=7, 16 symbols, 10% noise):

| System | Behavior | C(Î) |
|--------|----------|------|
| Counter | state = (state+1) % 16 | 2 ops |
| Echo | state = env_input | 1 op |
| Predictor | Frequency-table prediction of next env step | 5 ops |

### Results

| System | ρ_int | ρ_cond | Prediction Accuracy |
|--------|-------|--------|-------------------|
| Counter | **2.000** | **0.000** | N/A |
| Echo | 1.599 | **0.000** | 12.7% |
| Predictor | 0.413 | **0.073** | 84.5% |

Three properties validate ρ_cond:

1. **Counter exclusion**: ρ_cond = 0 for counter (no environment information extraction)
2. **Mirror exclusion**: ρ_cond = 0 for echo (I(S_{t+1}; E_t | S_t) = 0 because S_t = E_t already contains E_t)
3. **Inference detection**: ρ_cond > 0 only for the predictor, which genuinely integrates environmental information into an internal model

### The Mirror-Integration Distinction

The Echo result reveals a deeper structure. Echo perfectly copies the environment yet scores zero. This is because ρ_cond distinguishes two modes of environmental coupling:

- **Mirroring**: S_t = E_t (identity mapping from environment to state). Since S_t already contains E_t, I(S_{t+1}; E_t | S_t) = 0.
- **Integration**: S_{t+1} = f(S_t, E_t) where f is a non-trivial function that transforms E_t through an internal model. New information about E_t appears in S_{t+1} beyond what S_t already encodes.

In the language of the Principle of Being: mirroring is a degenerate Î' (identity mapping); integration is a genuine Î' that transforms perception into updated potential.

### Parameter Sensitivity

| Noise level | Predictor ρ_cond | Accuracy |
|-------------|-----------------|----------|
| 0.0 | 0.057 | 99.8% |
| 0.1 | 0.073 | 84.5% |
| 0.5 | 0.117 | 22.0% |

Counter-intuitively, ρ_cond increases with noise while accuracy decreases. In a more stochastic environment, each bit of captured environmental information is informationally more valuable. This is the correct information-theoretic behavior: ρ_cond measures information extraction efficiency, not prediction accuracy.

### Relationship to Project ρ

The project's original definition ρ = I(S; Env) / Cost measures total environmental information in S (a static snapshot). Our ρ_cond measures the rate of environmental information integration (a dynamic process). They relate as position to velocity: ρ_project ≈ ∫ ρ_cond dt.

For detecting whether a system is *actively reasoning* (vs. merely existing in an information-rich state), ρ_cond is the appropriate measure.
