# Test Specification: Perplexity-to-Quantization Mapping

## 1. Objective
To quantify the "intelligence degradation" caused by varying levels of KV cache and weight quantization. This helps determine the "Optimal Intelligence Floor"—the point where further quantization results in a non-linear drop in reasoning capability.

## 2. Methodology
*   **Target Model:** [Select Model, e.g., Qwen-27B]
*   **Reference Standard:** The original FP16 weights (or highest available quantization).
*   **Test Dataset:** Use a standard benchmark dataset (e.g., WikiText-2 or a custom set of complex logic puzzles).
*   **Metric:** Perplexity (PPL), calculated as the exponentiated average negative log-likelihood of the test set.

## 3. Test Matrix (Variable Parameters)
| Test ID | Weight Quant | KV Cache Type | Context Size |
| :--- | :--- | :--- | :--- |
| PPL_REF | FP16 | FP16 | 2048 |
| PPL_W_Q8 | Q8_0 | FP16 | 2048 |
| PPL_W_Q4 | Q4_K_M | FP16 | 2048 |
| PPL_K_Q8 | Q4_K_M | Q8_0 | 2048 |
| PPL_K_Q4 | Q4_K_M | Q4_0 | 2048 |

## 4. Data Points to Capture
*   **Perplexity Score:** The primary metric.
*   **Delta PPL:** The percentage increase in perplexity relative to the Reference Standard.
*   **Inference Latency:** Time taken to process the test set (to track the trade-off).

## 5. Application Implementation Hint
Integrate a "Perplexity Calculator" module that uses a small, fixed dataset. When a user saves a new configuration, the app runs this background task and attaches a "Perplexity Penalty" score to the config profile.

