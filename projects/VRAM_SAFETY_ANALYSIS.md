# Test Specification: VRAM Safety & OOM Prediction

## 1. Objective
To create a predictive model for Out-Of-Memory (OOM) events, specifically accounting for "Compaction Spikes"—the transient VRAM usage that occurs when the KV cache is reorganized.

## 2. Methodology
*   **Target Model:** [Select Model]
*   **Test Pattern:** Stress testing the context window until failure.
*   **Metric:** "Safety Margin" (Available VRAM - Peak Transient VRAM).

## 3. Test Matrix (Variable Parameters)
*   **Variable 1:** KV Cache Quantization (`f16`, `q8_0`, `q4_0`).
*   **Variable 2:** Context Window Size.
*   **Variable 3:** GPU Model (if running on multiple cards).

## 4. Data Points to Capture
*   **Static VRAM:** Memory used by weights + OS.
*   **Dynamic VRAM:** Memory used by the KV cache at current context.
*   **Peak Transient VRAM:** The highest recorded VRAM usage just before a compaction event or crash.
*   **Failure Threshold:** The context length where `Peak Transient VRAM > Total VRAM`.

## 5. Application Implementation Hint
Implement a "Safety Buffer" calculator. 
**Formula:** `Predicted_Peak = (Weight_Size) + (Context_Size * KV_Per_Token) * (1 + Compaction_Coefficient)`.
The `Compaction_Coefficient` is derived from your benchmarks (e.g., if compaction uses 15% extra memory, the coefficient is 0.15). Use this to color-code your config UI: **Green** (Safe), **Yellow** (Risk of OOM), **Red** (Guaranteed OOM).
