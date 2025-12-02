import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login
import os
import contextlib
from typing import Tuple, Optional, Dict, List, Union
from tqdm import tqdm
from dataclasses import dataclass

# Set seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)

@dataclass
class CausalTraceResult:
    scores: np.ndarray
    tokens: List[str]
    clean_prob: float
    corrupt_prob: float
    subject: str
    model_name: str

class CausalTracer:
    def __init__(self, model_name: str, token: Optional[str] = None):
        if token:
            login(token=token)
        
        self.device = self._get_device()
        
        # Use float16 or bfloat16 depending on hardware support for efficiency
        if self.device == "cuda":
            self.dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        elif self.device == "mps":
            self.dtype = torch.float32
        else:
            self.dtype = torch.float32
        
        print(f"--> Loading {model_name} on {self.device} ({self.dtype})...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # NOTE: avoiding device_map="auto" is correct here. 
        # 'accelerate' hooks interfere with manual forward hooks used in tracing.
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            dtype=self.dtype
        ).to(self.device).eval()
        
        self.layers = self._locate_layers()
        print(f"--> Model loaded. Tracing across {len(self.layers)} layers.")

    def _get_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _locate_layers(self) -> nn.ModuleList:
        """
        Dynamically finds the transformer block container to support various architectures 
        (Llama, Gemma, GPT-J, etc.).
        """
        # Common structural patterns in HF models
        candidates = ["model.layers", "model.model.layers", "transformer.h", "gpt_neox.layers"]
        
        for cand in candidates:
            parts = cand.split(".")
            curr = self.model
            found = True
            for part in parts:
                if hasattr(curr, part):
                    curr = getattr(curr, part)
                else:
                    found = False
                    break
            if found and isinstance(curr, nn.ModuleList):
                return curr
                
        raise ValueError(f"Could not locate layer stack in {type(self.model)}. Structure unknown.")

    def _get_token_indices(self, prompt: str, subject: str) -> Tuple[torch.Tensor, int, int]:
        """
        Robustly maps a subject string to token indices, handling whitespace variance.
        """
        enc = self.tokenizer(prompt, return_offsets_mapping=True, return_tensors="pt")
        input_ids = enc["input_ids"].to(self.device)
        offsets = enc["offset_mapping"][0].cpu().numpy()
        
        # 1. Find character span
        start_char = prompt.find(subject)
        if start_char == -1:
            raise ValueError(f"Subject '{subject}' not found in prompt.")
        end_char = start_char + len(subject)

        # 2. Map to tokens (Inclusive of partial overlaps)
        s_idx, e_idx = -1, -1
        for i, (o_start, o_end) in enumerate(offsets):
            if o_start == o_end: continue # Skip special tokens like BOS
            
            # Intersection check
            if max(start_char, o_start) < min(end_char, o_end):
                if s_idx == -1: s_idx = i
                e_idx = i + 1
        
        if s_idx == -1:
             raise ValueError(f"Could not align subject '{subject}' to tokens.")
             
        return input_ids, s_idx, e_idx

    @contextlib.contextmanager
    def _trace_hook(self, layer_idx: int, storage: Optional[Dict] = None, 
                   key: Optional[int] = None, do_patch: bool = False, 
                   patch_val: Optional[torch.Tensor] = None, token_indices: Optional[torch.Tensor] = None):
        """
        Unified hook for caching (Clean Run) and patching (Restoration Run).
        Supports batched patching.
        """
        module = self.layers[layer_idx]
        
        def hook_fn(mod, inp, out):
            # HF models output tuples (hidden_state, past_key_values, ...)
            # We only care about the first element (hidden state)
            is_tuple = isinstance(out, tuple)
            act = out[0] if is_tuple else out

            if not do_patch:
                # -- CLEAN RUN: CACHE --
                if storage is not None:
                    # Move to CPU to save GPU memory during heavy generation
                    storage[key] = act.detach().cpu().clone()
                return out
            else:
                # -- DIRTY RUN: PATCH --
                if patch_val is not None and token_indices is not None:
                    # We modify the tensor in-place to avoid breaking the graph for subsequent layers
                    # though 'out' is usually a new tensor anyway.
                    patched = act.clone() # Clone to avoid modifying original corrupted flow elsewhere
                    
                    # Move patch value to device only when needed
                    pv = patch_val.to(act.device).type(act.dtype)
                    
                    # Batched Patching
                    # patched shape: [batch_size, seq_len, hidden_dim]
                    if isinstance(token_indices, torch.Tensor) and token_indices.ndim > 0:
                        # Advanced indexing for batch
                        batch_indices = torch.arange(patched.shape[0], device=patched.device)
                        patched[batch_indices, token_indices, :] = pv[0, token_indices, :]
                    else:
                        # Fallback for single index
                        idx = token_indices if isinstance(token_indices, int) else token_indices.item()
                        if 0 <= idx < patched.shape[1]:
                            patched[:, idx, :] = pv[:, idx, :]
                    
                    return (patched,) + out[1:] if is_tuple else patched
                return out

        handle = module.register_forward_hook(hook_fn)
        try:
            yield handle
        finally:
            handle.remove()

    def trace(self, prompt: str, subject: str, noise_scale: float = 0.15, specific_target: str = None, batch_size: int = 10) -> CausalTraceResult:
        ids, s_idx, e_idx = self._get_token_indices(prompt, subject)
        
        # --- 1. Setup Target ID ---
        with torch.no_grad():
            clean_out = self.model(ids)
            clean_logits = clean_out.logits[0, -1]
            clean_probs = torch.softmax(clean_logits, dim=0)
            
            if specific_target:
                full_text_ids = self.tokenizer.encode(prompt + specific_target, return_tensors="pt")[0]
                target_id = full_text_ids[-1]
            else:
                target_id = torch.argmax(clean_probs).item()
            
            base_p = clean_probs[target_id].item()
        
        # --- 2. Clean Run: Cache Hidden States ---
        clean_acts = {}
        handles = []
        
        # Register hooks for all layers
        for i in range(len(self.layers)):
            def make_hook_fn(layer_idx):
                def _hook(mod, inp, out):
                    act = out[0] if isinstance(out, tuple) else out
                    clean_acts[layer_idx] = act.detach().cpu().clone()
                return _hook
            
            handles.append(self.layers[i].register_forward_hook(make_hook_fn(i)))
        
        # Run forward pass to fill clean_acts
        with torch.no_grad():
            self.model(ids)
        
        # Remove all hooks
        for h in handles: h.remove()
        
        # --- 3. Create Corrupted Embedding ---
        embed_layer = self.model.get_input_embeddings()
        clean_embeds = embed_layer(ids)
        
        # Gaussian noise added to the subject tokens only
        noise_std = clean_embeds.std().item() * noise_scale
        noise_tensor = torch.randn_like(clean_embeds[:, s_idx:e_idx, :]) * noise_std
        
        corrupt_embeds = clean_embeds.clone()
        corrupt_embeds[:, s_idx:e_idx, :] += noise_tensor.to(clean_embeds.dtype)
        
        with torch.no_grad():
            corr_out = self.model(inputs_embeds=corrupt_embeds)
            corr_p = torch.softmax(corr_out.logits[0, -1], dim=0)[target_id].item()

        print(f"Prompt: '{prompt}' | Target: '{self.tokenizer.decode(target_id)}'")
        print(f"Probabilities: Clean {base_p:.4f} -> Corrupted {corr_p:.4f}")

        # --- 4. Restoration Run (The Scan) ---
        num_tokens = ids.shape[1]
        num_layers = len(self.layers)
        # +1 for Embeddings layer
        scores = np.zeros((num_layers + 1, num_tokens), dtype=np.float32)

        pbar = tqdm(total=(num_layers + 1) * num_tokens, desc="Tracing Causal Effects")
        
        # 4a. Trace Embeddings (Layer -1)
        # We restore embeddings by mixing clean and corrupt embeddings at specific tokens
        for t_start in range(0, num_tokens, batch_size):
            t_end = min(t_start + batch_size, num_tokens)
            current_batch_size = t_end - t_start
            
            # Start with corrupt embeddings for the whole batch
            batch_embeds = corrupt_embeds.repeat(current_batch_size, 1, 1)
            
            # Restore specific tokens to clean state
            # For each batch element i (corresponding to token t_start + i), 
            # we restore the embedding at position (t_start + i)
            for i in range(current_batch_size):
                token_pos = t_start + i
                batch_embeds[i, token_pos, :] = clean_embeds[0, token_pos, :]
            
            with torch.no_grad():
                res = self.model(inputs_embeds=batch_embeds)
                probs = torch.softmax(res.logits[:, -1, :], dim=-1)[:, target_id]
                
                denom = (base_p - corr_p)
                if abs(denom) < 1e-6:
                    batch_scores = torch.zeros_like(probs)
                else:
                    batch_scores = (probs - corr_p) / denom
                
                scores[0, t_start:t_end] = batch_scores.cpu().numpy()
            
            pbar.update(current_batch_size)

        # 4b. Trace Hidden Layers
        for l in range(num_layers):
            for t_start in range(0, num_tokens, batch_size):
                t_end = min(t_start + batch_size, num_tokens)
                current_batch_size = t_end - t_start
                
                batch_embeds = corrupt_embeds.repeat(current_batch_size, 1, 1)
                batch_indices = torch.arange(t_start, t_end, device=self.device)
                
                with self._trace_hook(l, do_patch=True, patch_val=clean_acts[l], token_indices=batch_indices):
                    with torch.no_grad():
                        res = self.model(inputs_embeds=batch_embeds)
                        probs = torch.softmax(res.logits[:, -1, :], dim=-1)[:, target_id]
                        
                        denom = (base_p - corr_p)
                        if abs(denom) < 1e-6:
                            batch_scores = torch.zeros_like(probs)
                        else:
                            batch_scores = (probs - corr_p) / denom
                        
                        # Store at l+1 because index 0 is embeddings
                        scores[l + 1, t_start:t_end] = batch_scores.cpu().numpy()
                
                pbar.update(current_batch_size)
        pbar.close()

        tokens = [self.tokenizer.decode([t]).replace(' ', ' ') for t in ids[0].tolist()]
        
        return CausalTraceResult(
            scores=scores,
            tokens=tokens,
            clean_prob=base_p,
            corrupt_prob=corr_p,
            subject=subject,
            model_name=self.model.config._name_or_path
        )

    @staticmethod
    def plot_results(result: CausalTraceResult):
        plt.figure(figsize=(12, 8))
        
        # Create labels for y-axis
        # 0 is Embeddings, then 1..N are layers
        yticklabels = ["Emb"] + [str(i) for i in range(result.scores.shape[0] - 1)]
        
        # If too many layers, sparse labels
        if len(yticklabels) > 20:
            sparse_labels = []
            for i, label in enumerate(yticklabels):
                if i == 0 or label == "Emb":
                    sparse_labels.append(label)
                elif label.isdigit() and int(label) % 5 == 0:
                    sparse_labels.append(label)
                else:
                    sparse_labels.append("")
            yticklabels = sparse_labels

        sns.heatmap(
            result.scores, 
            xticklabels=result.tokens, 
            yticklabels=yticklabels,
            cmap="Purples", 
            cbar_kws={'label': 'Normalized Causal Impact'}
        )
        
        plt.xlabel("Token Position", fontsize=16)
        plt.ylabel("Layer Depth", fontsize=16)
        plt.title(f"Causal Trace: '{result.subject}' on {result.model_name}", fontsize=20)
        plt.xticks(rotation=45, ha='right', fontsize=14)
        plt.yticks(fontsize=14)
        plt.tight_layout()
        plt.show()

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict

@dataclass
class KnowledgeTriplet:
    subject: str
    relation_template: str
    target: str
    region: str # 'LatAm' or 'GlobalNorth'

class ComparativeExperiment:
    def __init__(self, tracer: CausalTracer):
        self.tracer = tracer
        self.results = {"LatAm": [], "GlobalNorth": []}
    
    def run_experiment(self, triplets: List[KnowledgeTriplet]):
        print(f"--> Iniciando experimento con {len(triplets)} tripletas...")
        
        for item in triplets:
            prompt = item.relation_template.format(item.subject)
            try:
                result = self.tracer.trace(
                    prompt=prompt, 
                    subject=item.subject, 
                    specific_target=item.target,
                    noise_scale=0.1
                )
                
                # Identificamos índices para métricas agregadas
                _, s_idx, e_idx = self.tracer._get_token_indices(prompt, item.subject)
                last_subject_idx = e_idx - 1
                subject_impact = result.scores[:, last_subject_idx]
                
                self.results[item.region].append({
                    "subject_impact": subject_impact,
                    "full_scores": result.scores,
                    "subject": item.subject,
                    "tokens": result.tokens  # <--- [NUEVO] Guardamos los tokens aquí
                })
                
            except Exception as e:
                print(f"Error procesando {item.subject}: {e}")

    def plot_comparative_heatmaps(self, subject_latam: str, subject_north: str):
        res_latam = next((r for r in self.results["LatAm"] if r["subject"] == subject_latam), None)
        res_north = next((r for r in self.results["GlobalNorth"] if r["subject"] == subject_north), None)
        
        if not res_latam or not res_north:
            print("No se encontraron los sujetos especificados.")
            return

        # Ajuste de figura
        fig, axes = plt.subplots(1, 2, figsize=(22, 8), sharey=True)
        
        # Escala de color unificada
        max_val = max(res_latam["full_scores"].max(), res_north["full_scores"].max())
        
        # --- Gráfico LatAm ---
        sns.heatmap(
            res_latam["full_scores"],
            ax=axes[0],
            cmap="Purples",
            vmin=0, vmax=max_val,
            cbar=False,
            xticklabels=res_latam["tokens"],  # <--- [NUEVO] Asignamos los tokens
            yticklabels=True
        )
        axes[0].set_title(f"LatAm: {subject_latam}", fontsize=20)
        axes[0].set_xlabel("Token Position", fontsize=16)
        axes[0].set_ylabel("Layer Depth", fontsize=16)
        axes[0].set_xticklabels(res_latam["tokens"], rotation=45, ha='right', fontsize=14) # Rotación para lectura
        axes[0].tick_params(axis='y', labelsize=14)
        
        # --- Gráfico Global North ---
        sns.heatmap(
            res_north["full_scores"],
            ax=axes[1],
            cmap="Purples",
            vmin=0, vmax=max_val,
            cbar=True,
            cbar_kws={'label': 'Normalized Causal Impact'},
            xticklabels=res_north["tokens"],  # <--- [NUEVO] Asignamos los tokens
            yticklabels=False # Ocultamos Y labels repetidos
        )
        axes[1].set_title(f"Global North: {subject_north}", fontsize=20)
        axes[1].set_xlabel("Token Position", fontsize=16)
        axes[1].set_xticklabels(res_north["tokens"], rotation=45, ha='right', fontsize=14) # Rotación para lectura

        plt.suptitle(f"Comparación Topológica: {subject_latam} vs {subject_north}", fontsize=24)
        plt.tight_layout()
        plt.show()

    def analyze_and_plot(self):
        # Preparar datos para visualizar
        # Vamos a comparar el perfil de capas (Layer Depth) vs Impacto en el Sujeto
        
        avg_impact = {}
        std_impact = {}
        
        plt.figure(figsize=(14, 6))
        
        # Subplot 1: Perfil de Activación por Capas (Line Plot)
        plt.subplot(1, 2, 1)
        
        colors = {"LatAm": "orange", "GlobalNorth": "blue"}
        
        for region in ["LatAm", "GlobalNorth"]:
            data = [r["subject_impact"] for r in self.results[region]]
            if not data: continue
            
            # Stack data: (n_samples, n_layers)
            stack = np.stack(data)
            mean_curve = np.mean(stack, axis=0)
            std_curve = np.std(stack, axis=0)
            
            avg_impact[region] = mean_curve
            
            x = range(len(mean_curve))
            plt.plot(x, mean_curve, label=f"{region} (n={len(data)})", color=colors[region], linewidth=2)
            plt.fill_between(x, mean_curve - std_curve, mean_curve + std_curve, color=colors[region], alpha=0.2)
            
        plt.title("Impacto Causal Promedio en el Último Token del Sujeto", fontsize=18)
        plt.xlabel("Profundidad de la Capa", fontsize=16)
        plt.ylabel("Impacto Causal Normalizado", fontsize=16)
        plt.legend(fontsize=14)
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        plt.grid(True, alpha=0.3)

        # Subplot 2: Mapa de Calor Diferencial (Aggregation)
        # Para hacer un heatmap promedio, necesitamos una dimensión X fija.
        # Tomaremos: [Subject_Last_Token, Next_Token, ..., Last_Prompt_Token]
        # Simplificación: Visualizaremos la diferencia en el vector de capas (eje Y) 
        # para el token del sujeto (el más crítico según ROME).
        
        plt.subplot(1, 2, 2)
        if "LatAm" in avg_impact and "GlobalNorth" in avg_impact:
            # Asegurar mismas dimensiones
            min_len = min(len(avg_impact["LatAm"]), len(avg_impact["GlobalNorth"]))
            diff = avg_impact["GlobalNorth"][:min_len] - avg_impact["LatAm"][:min_len]
            
            # Crear heatmap vertical de una columna
            sns.heatmap(diff.reshape(-1, 1), cmap="RdBu_r", center=0, annot=True, fmt=".2f",
                       yticklabels=True, xticklabels=["Diff (North - LatAm)"], annot_kws={"size": 12})
            plt.title("Diferencial de Localización (Norte - LatAm)", fontsize=18)
            plt.ylabel("Capa", fontsize=16)
            plt.yticks(fontsize=14)
            plt.xticks(fontsize=14)
        
        plt.tight_layout()
        plt.show()

# --- DEFINICIÓN DE DATOS Y EJECUCIÓN ---

if __name__ == "__main__":
    # Configuración
    MODEL_ID = "google/gemma-2-2b" # O tu modelo de preferencia
    HF_TOKEN = os.getenv("HF_TOKEN")
    
    # Instanciar el Tracer original
    tracer = CausalTracer(MODEL_ID, token=HF_TOKEN)
    
    # Definir el Dataset (Sujeto, Relación, Objeto)
    # Nota: Usamos inglés para consistencia con modelos base, pero medimos entidades regionales.
    template = "The capital of {} is"
    # template = "La capital de {} es"
    
    dataset = [
        # LATAM
        KnowledgeTriplet("Chile", template, "Santiago", "LatAm"),
        KnowledgeTriplet("Peru", template, "Lima", "LatAm"),
        KnowledgeTriplet("Uruguay", template, "Montevideo", "LatAm"),
        
        # GLOBAL NORTH
        KnowledgeTriplet("France", template, "Paris", "GlobalNorth"),
        KnowledgeTriplet("Japan", template, "Tokyo", "GlobalNorth"),
        KnowledgeTriplet("Canada", template, "Ottawa", "GlobalNorth"),
    ]
    
    # Correr Experimento
    exp = ComparativeExperiment(tracer)
    exp.run_experiment(dataset)
    # exp.analyze_and_plot()
    exp.plot_comparative_heatmaps("Chile", "Canada")
    exp.plot_comparative_heatmaps("Peru", "Japan")
