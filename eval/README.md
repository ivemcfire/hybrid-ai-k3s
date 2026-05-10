# Eval harness

Routing-decision test harness for the hybrid-ai workflow. Sends staged coding tasks to the local model and grades outputs against ground truth.

Stages probe increasing difficulty:
- **Step 1** — boilerplate generation (sample.csv parser)
- **Step 2** — single-file bug fix
- **Step 3** — multi-step composition

If local model passes Step 1+2 but fails Step 3, route Step 3 to cloud Claude.

## Usage

Wake `.50` first (see `../scripts/wol.sh`), then:
```bash
./run_local.sh step1_prompt.txt           # default model: qwen2.5-coder:14b
./run_local.sh step2_prompt.txt
./run_local.sh step3_prompt.txt qwen2.5-coder:7b-instruct  # override model
python3 eval_step1.py
python3 eval_step2.py
python3 eval_step3.py
```

Outputs (`step*_output.txt`, `step*_err.log`) are regenerated each run and gitignored.

## Tuning context

Local box: Windows desktop `192.168.100.50:11500`, RTX 3060 12GB, Ollama 0.22+. VRAM cap + flash attention applied via `ollama-tune-vram-cap.ps1` (laptop `~/bin/`). See companion memory `~/.claude/projects/-home-ivalin/memory/reference_hybrid_ai_tuning.md` for backend candidates (Ollama vs vLLM vs Unsloth) and quant guidance (Q4_K_M / Q5_K_M).
