# ±10 percentage-point sensitivity

LOW/BASE/HIGH alter each formal V2 model's trial-weighted evaluation pass rate by ±0.10 absolute, clamped to [0,1]. AI execution cost is held at its fully measured D5 provider-cost mean; nurse fallback uses the assignment assumption. This is a scenario, not a production forecast.

Across all independent LOW/BASE/HIGH combinations for each pair, stable pairwise cost orderings: **4**; orderings that can change or tie: **2**. A changed ordering means no pairwise economic conclusion is robust across the full assumed band.

Stable pairs: openai_gpt4o_mini_v2 vs qwen3_30b_v2, openai_gpt4o_mini_v2 vs mistral_small_3_2_v2, openai_gpt4o_mini_v2 vs gemini2_5_flash_v2, qwen3_30b_v2 vs gemini2_5_flash_v2.

Unstable pairs: qwen3_30b_v2 vs mistral_small_3_2_v2, mistral_small_3_2_v2 vs gemini2_5_flash_v2.
