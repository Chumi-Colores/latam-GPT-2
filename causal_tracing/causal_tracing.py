import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login
import os

class CausalTracer:
    def __init__(self, model_name, token=None):
        if token:
            login(token=token)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(self.device).eval()
        self.hooks = []
        self._locate_layers()

    def _locate_layers(self):
        candidate = None
        candidate_name = ""
        for name, module in self.model.named_modules():
            if isinstance(module, nn.ModuleList) and len(module) > 0:
                low = name.lower()
                if any(k in low for k in ("layer", "layers", "h", "block", "blocks", "transformer")):
                    candidate = module
                    candidate_name = name
                    break
                if candidate is None:
                    candidate = module
                    candidate_name = name
        if candidate is None:
            raise ValueError("No se encontró ModuleList de capas.")
        self.layers = candidate
        self.layer_name_format = candidate_name + ".{}"
        print(f"Usando ModuleList en '{candidate_name}' con {len(self.layers)} capas.")

    def _get_token_indices(self, prompt, subject):
        enc = self.tokenizer(prompt, return_offsets_mapping=True, return_tensors="pt", truncation=False)
        offsets = enc["offset_mapping"][0].cpu().numpy()
        input_ids = enc["input_ids"].to(self.device)
        start_char = prompt.find(subject)
        if start_char == -1:
            return input_ids, None, None
        end_char = start_char + len(subject)

        s_idx, e_idx = -1, -1
        for i, (o_start, o_end) in enumerate(offsets):
            if o_start == 0 and o_end == 0:
                continue
            if o_end > start_char and o_start < end_char:
                if s_idx == -1:
                    s_idx = i
                e_idx = i + 1
        if s_idx == -1:
            return input_ids, None, None
        return input_ids, s_idx, e_idx

    def _register_hook(self, layer_idx, storage=None, key=None, do_patch=False, patch_val=None, token_idx=None):
        module = self.layers[layer_idx]
        def hook(mod, inp, out):
            act = out[0] if isinstance(out, tuple) else out
            if not do_patch:
                storage[key] = act.detach().clone()
                return out
            else:
                pv = patch_val.to(act.device)
                patched = act.clone()
                if 0 <= token_idx < patched.shape[1]:
                    patched[:, token_idx, :] = pv[:, token_idx, :].to(patched.dtype)
                return (patched,) + out[1:] if isinstance(out, tuple) else patched
        return module.register_forward_hook(hook)

    def trace(self, prompt, subject, noise=0.15, specific_target=None):
        ids, s_idx, e_idx = self._get_token_indices(prompt, subject)
        if s_idx is None:
            raise ValueError("Subject not found in prompt.")
        clean_acts = {}
        hooks = [self._register_hook(i, clean_acts, i) for i in range(len(self.layers))]
        with torch.no_grad():
            out = self.model(ids)
            probs = torch.softmax(out.logits[0, -1], dim=0)
            if specific_target:
                tgt_ids = self.tokenizer.encode(specific_target, add_special_tokens=False)
                if len(tgt_ids) != 1:
                    print("WARNING: specific_target contiene >1 token. Usando primer token solo.")
                target_id = tgt_ids[0]
            else:
                target_id = torch.argmax(probs).item()
            base_p = probs[target_id].item()
        for h in hooks: h.remove()

        embeds = self.model.get_input_embeddings()(ids)
        noise_tensor = torch.randn_like(embeds[:, s_idx:e_idx, :], device=embeds.device) * noise
        corrupt_embeds = embeds.clone()
        corrupt_embeds[:, s_idx:e_idx, :] += noise_tensor
        with torch.no_grad():
            corr_logits = self.model(inputs_embeds=corrupt_embeds).logits
            corr_p = torch.softmax(corr_logits[0, -1], dim=0)[target_id].item()

        num_tokens = ids.shape[1]
        scores = np.zeros((len(self.layers), num_tokens), dtype=float)
        for l in range(len(self.layers)):
            for t in range(num_tokens):
                if l not in clean_acts:
                    print(f"WARNING: no clean activation for layer {l}; skipping")
                    continue
                h = self._register_hook(l, None, None, do_patch=True, patch_val=clean_acts[l], token_idx=t)
                with torch.no_grad():
                    res = self.model(inputs_embeds=corrupt_embeds)
                    p = torch.softmax(res.logits[0, -1], dim=0)[target_id].item()
                    scores[l, t] = (p - corr_p) / (base_p - corr_p + 1e-10)
                h.remove()
        tokens = [self.tokenizer.decode(t) for t in ids[0].tolist()]
        return scores, tokens

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    tracer = CausalTracer("google/gemma-2b", os.getenv("HF_TOKEN"))
    scores, tokens = tracer.trace("The capital of Chile is", "of")
    plt.figure(figsize=(10, 6))
    plt.imshow(scores, aspect='auto', origin='lower', cmap='magma')
    plt.xticks(range(len(tokens)), tokens, rotation=45, ha='right')
    plt.colorbar(label="AIE Score")
    plt.title("Causal Trace: Hidden State Restoration")
    plt.tight_layout()
    plt.show()
