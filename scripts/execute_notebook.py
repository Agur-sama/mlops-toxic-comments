from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "coursework_toxicity.ipynb"

nb = nbformat.read(NOTEBOOK, as_version=4)
client = NotebookClient(
    nb,
    timeout=3600,
    kernel_name="python3",
    allow_errors=False,
    # Намеренно запускаем из каталога notebooks: так автоматическая проверка
    # воспроизводит обычное открытие файла пользователем и тестирует поиск ROOT.
    resources={"metadata": {"path": str(NOTEBOOK.parent)}},
)
client.execute()
nbformat.write(nb, NOTEBOOK)
print(f"Executed notebook saved to {NOTEBOOK}")

