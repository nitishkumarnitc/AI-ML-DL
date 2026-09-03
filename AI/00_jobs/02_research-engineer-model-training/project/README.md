# Run it

```bash
pip install torch
python run.py
python run.py --dpo-epochs 150 --beta 0.3          # tune the DPO run
python run.py --save-checkpoint dpo_model.pt        # persist the trained model
python run.py --help
```

Takes ~8-10 seconds. Runs a real SFT -> DPO pipeline (10 preference pairs, hand-rolled tiny LM, real DPO loss math) and reports:

1. **Preference win-rate** — raw vs length-normalized — across base/SFT/DPO. The raw metric is a length-biased artifact (~100% regardless of training); the normalized one is what actually shows the DPO stage working.
2. **Held-out response length** before vs after each stage.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
