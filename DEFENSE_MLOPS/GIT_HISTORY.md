# Git-история и публикация

## Репозиторий

- GitHub: <https://github.com/Agur-sama/mlops-toxic-comments>
- основная ветка: `main`;
- рабочая ветка финального аудита: `codex/mlops-final-audit`;
- Pull Request: <https://github.com/Agur-sama/mlops-toxic-comments/pull/1>;
- итоговый tag после merge: `v1.2.0`.

## Важные исходные коммиты

- `1fe86b49b85f242e7fd0635b888059c1389384df` — воспроизводимый baseline
  обучения и code version, записанная в MLflow runs;
- `c415bc3` — versioned inference service и MLOps pipeline;
- `17b430e` — merge service/reproducibility;
- `3171747` — документация для сдачи;
- `6f09f335a359bd57dca5dd6640b1313b2b2af327` — чистый baseline
  `v1.0.0`, опубликованный как исходная `main` нового репозитория;
- `a92efb8` — воспроизводимая сборка полного API+UI стека;
- `0ef405f` — pinned Docker digest, CI/GHCR hardening и portable artifacts;
- `83cb82b` — упрощение Streamlit UI по запросу владельца.

После этих коммитов документация добавляется отдельным атомарным коммитом в
PR №1. Лабораторная история `mlops_submission/` в новый репозиторий не
переносится; исходный локальный репозиторий и его история не переписывались.

## Как проверить итоговый SHA

```bash
git fetch --tags origin
git rev-parse 'v1.2.0^{commit}'
git show --no-patch --decorate v1.2.0
```

SHA самого release commit нельзя корректно записать внутрь содержимого того же
commit: изменение строки изменит SHA. Поэтому authority — подписанный Git tag и
команда выше; полный фактический SHA также указывается в итоговом сообщении о
сдаче.

## CI

- workflow: <https://github.com/Agur-sama/mlops-toxic-comments/actions/workflows/ci.yml>;
- PR checks: <https://github.com/Agur-sama/mlops-toxic-comments/pull/1/checks>.
- подтверждённый PR run №3:
  <https://github.com/Agur-sama/mlops-toxic-comments/actions/runs/45493243912> —
  `quality` и `image` завершены успешно, `publish` пропущен по условию tag-only.

На защите откройте run для `v1.2.0`: он должен содержать успешные jobs
`quality`, `image`, `publish` и публикацию API+UI в GHCR.
