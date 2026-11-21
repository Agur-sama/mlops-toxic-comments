from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .metrics import classification_metrics, select_f1_threshold
from .preprocessing import minimal_clean


def run_bert_training(
    splits: dict[str, pd.DataFrame],
    config: dict,
    results_dir: Path,
    models_dir: Path,
    predictions_dir: Path,
    variant_name: str = "distilbert",
) -> pd.DataFrame:
    try:
        import torch
        from datasets import Dataset, DatasetDict
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            EarlyStoppingCallback,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise RuntimeError(
            "BERT dependencies are not installed. Install torch, transformers, datasets, accelerate."
        ) from exc

    cfg = config["bert"]
    max_train_samples = cfg.get("max_train_samples")
    prepared: dict[str, Dataset] = {}
    for name, frame in splits.items():
        subset = frame
        if name == "train" and max_train_samples:
            n = min(int(max_train_samples), len(frame))
            toxic_n = max(1, int(round(n * frame["toxic"].mean())))
            subset = pd.concat([
                frame[frame.toxic == 1].sample(min(toxic_n, int(frame.toxic.sum())), random_state=42),
                frame[frame.toxic == 0].sample(n - min(toxic_n, int(frame.toxic.sum())), random_state=42),
            ]).sample(frac=1, random_state=42)
        prepared[name] = Dataset.from_dict(
            {
                "id": subset["id"].astype(str).tolist(),
                "text": subset["comment_text"].map(minimal_clean).tolist(),
                "label": subset["toxic"].astype(int).tolist(),
            }
        )
    dataset = DatasetDict(prepared)
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name"], use_fast=True)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=int(cfg["max_length"]))

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
    model = AutoModelForSequenceClassification.from_pretrained(cfg["model_name"], num_labels=2)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        probs = torch.softmax(torch.tensor(logits), dim=1).numpy()[:, 1]
        preds = (probs >= 0.5).astype(int)
        return {
            "f1": f1_score(labels, preds, zero_division=0),
            "precision": precision_score(labels, preds, zero_division=0),
            "recall": recall_score(labels, preds, zero_division=0),
            "roc_auc": roc_auc_score(labels, probs),
            "pr_auc": average_precision_score(labels, probs),
        }

    use_cuda = torch.cuda.is_available()
    use_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    output_dir = models_dir / variant_name
    args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=float(cfg["learning_rate"]),
        per_device_train_batch_size=int(cfg["train_batch_size"]),
        per_device_eval_batch_size=int(cfg["eval_batch_size"]),
        gradient_accumulation_steps=int(cfg["gradient_accumulation_steps"]),
        num_train_epochs=float(cfg["epochs"]),
        weight_decay=float(cfg["weight_decay"]),
        warmup_ratio=float(cfg["warmup_ratio"]),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="pr_auc",
        greater_is_better=True,
        fp16=use_cuda,
        use_mps_device=use_mps,
        report_to="none",
        seed=42,
        data_seed=42,
        save_total_limit=2,
        logging_steps=50,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    started = time.perf_counter()
    trainer.train()
    fit_seconds = time.perf_counter() - started
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    history_path = results_dir / f"{variant_name}_history.json"
    history_path.write_text(json.dumps(trainer.state.log_history, indent=2), encoding="utf-8")

    val_output = trainer.predict(tokenized["validation"])
    val_scores = torch.softmax(torch.tensor(val_output.predictions), dim=1).numpy()[:, 1]
    threshold_info = select_f1_threshold(val_output.label_ids, val_scores)
    threshold = threshold_info["threshold"]
    val_metrics, _ = classification_metrics(val_output.label_ids, val_scores, threshold, "probability")

    test_output = trainer.predict(tokenized["test"])
    test_scores = torch.softmax(torch.tensor(test_output.predictions), dim=1).numpy()[:, 1]
    test_metrics, test_pred = classification_metrics(test_output.label_ids, test_scores, threshold, "probability")
    predictions = splits["test"][["id", "comment_text", "toxic"]].iloc[: len(test_scores)].copy()
    predictions["score"] = test_scores
    predictions["prediction"] = test_pred
    predictions["model"] = variant_name
    predictions_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(predictions_dir / f"{variant_name}_test_predictions.csv", index=False)
    row = {
        "model": variant_name,
        "preprocessing": "minimal + model tokenizer",
        "vectorizer": cfg["model_name"],
        "parameters": json.dumps(cfg, sort_keys=True),
        "fit_seconds": fit_seconds,
        **{f"validation_{k}": v for k, v in val_metrics.items()},
        **{f"test_{k}": v for k, v in test_metrics.items()},
    }
    table = pd.DataFrame([row])
    results_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(results_dir / f"{variant_name}_results.csv", index=False)
    return table

