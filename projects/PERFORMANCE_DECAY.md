# Test Specification: Context-Length Performance Decay

## 1. Objective
To identify the "Performance Cliff"—the specific context length where GPU hardware constraints (tiling, memory bandwidth, or fragmentation) cause a significant drop in Tokens Per Second (TPS).

## 2. Methodology
*   **Target Model:** [Select Model]
*   **Test Pattern:** A "sliding window" approach where the context grows incrementally.
*   **Metric:** Tokens Per Second (TPS) during the *generation* phase (not the prefill phase).

## 3. Test Matrix (Variable Parameters)
*   **X-Axis (Context Size):** 1k, 2k, 4k, 8k, 16k, 32k, 64k, 128k, 192k, 256k.
*   **Y-Axis (Fixed Config):** [Select a stable config, e.g., Q4_K_M + Q8_0 KV].

## 4. Data Points to Capture
*   **Generation TPS:** Speed of producing new tokens.
*   **Prefill TPS:** Speed of processing the initial prompt.
*   **VRAM Usage:** Real-time MB usage at each step.
*   **Slope of Decay:** The rate at which TPS drops as context increases ($\Delta TPS / \Delta Context$).

## 5. Application Implementation Hint
Create a "Performance Curve" visualization in your UI. As the user moves a "Context Slider," the app should display a ghosted curve showing where they are likely to hit the performance cliff based on previous benchmarks.

