# GreenLight 2 Greenhouse Simulator

An interactive greenhouse simulation and decision-support workbench that connects a polished browser interface to the 28-state GreenLight-Gym2 scientific model. Explore climate control, crop response, actuator behavior, measured Amsterdam weather, and resource use in one local application.

[![CI](https://github.com/benbenbeatit912002/Greenlight-simulation/actions/workflows/ci.yml/badge.svg)](https://github.com/benbenbeatit912002/Greenlight-simulation/actions/workflows/ci.yml)

[Overview](#overview) · [Product direction](#product-direction) · [Quick start](#quick-start) · [Model modes](#model-modes) · [Model card](MODEL_CARD.md) · [Contributing](CONTRIBUTING.md) · [繁體中文](#繁體中文)

## Overview

The simulator is designed to be useful in two settings:

- **Scientific local mode** runs the GreenLight-Gym2 CasADi/CVODES model with 28 states, six absolute controls, 15-minute steps, and measured Amsterdam weather.
- **Installation-free interaction** uses a clearly labelled browser approximation so the interface remains explorable when the scientific backend is unavailable.

The interface shows indoor and outdoor climate, crop state, control targets, actuator openings, limit warnings, trends, energy use, CO₂ use, and estimated cost. It supports both a rule-based controller and manual control of `uBoil`, `uCO2`, `uThScr`, `uVent`, `uLamp`, and `uBlScr`.

## Product direction

This project is an **explainable pre-deployment decision-support workbench**, not a production greenhouse controller. Run one strategy, save it as a baseline, reset, and run a candidate to the same horizon. Numeric deltas remain hidden when runs use different engines, unresolved or different model provenance, different cost assumptions, or unequal horizons. Weather context stays visible so a user can distinguish a control comparison from a broader scenario comparison.

The first comparison covers heating, supplemental lighting, CO₂, estimated cost, end-state climate alerts, and fruit dry mass. These are trade-offs rather than a single winner score, and the interface explicitly states that simulation output is not production advice.

The evidence, target user, scope boundaries, and staged roadmap are documented in [`PRODUCT_STRATEGY.md`](PRODUCT_STRATEGY.md). Engine provenance, economic assumptions, validation status, and unsupported uses are documented in [`MODEL_CARD.md`](MODEL_CARD.md).

## Quick start

### Browser approximation

This mode demonstrates the interface without importing the external GreenLight-Gym2 source tree:

```powershell
git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git
Set-Location .\Greenlight-simulation
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --python 3.12
& '.\.venv\Scripts\python.exe' -B .\server.py --engine browser
```

Open <http://127.0.0.1:4173/>.

### Full scientific model

Install the optional open-source scientific dependencies inside this repository, then point the adapter to a read-only GreenLight-Gym2 source checkout:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:GREENLIGHT_GYM_PATH = 'C:\path\to\GreenLight-Gym2'
uv sync --extra greenlight --python 3.12
& '.\.venv\Scripts\python.exe' -B .\server.py --engine glgym
```

The control-panel badge should report **GreenLight 2 full model**. The adapter imports GreenLight-Gym2 read-only; it does not install into or modify that source checkout.

## Model modes

| Mode | Behavior | Intended use |
| --- | --- | --- |
| `--engine glgym` | Requires the full GreenLight-Gym2 model and stops if initialization fails. | Scientific-model validation and local research use. |
| `--engine auto` | Prefers the full model and falls back to the labelled browser approximation when unavailable. | Normal local use and presentations. |
| `--engine browser` | Serves the interface without constructing the scientific model. | UI demonstrations and lightweight review. |

The active engine is always visible in the interface and available from `GET /api/status`. Approximation output is never presented as a full scientific result.

## Architecture

```mermaid
flowchart LR
    UI["HTML / CSS / JavaScript interface"] -->|"same-origin JSON"| API["Local Python HTTP API"]
    API --> ADAPTER["GreenLight adapter"]
    ADAPTER -->|"read-only source import"| MODEL["GreenLight-Gym2 · 28-state CasADi model"]
    UI --> FALLBACK["Labelled browser approximation"]
```

- The server binds to `127.0.0.1` by default and does not enable CORS.
- API mutations use monotonic revisions to prevent stale tabs from overwriting newer state.
- The frontend stops overlapping simulation loops and safely falls back if the Python backend disappears.
- Runtime dependencies, caches, logs, and generated files stay inside this repository.

## Validation

The deterministic browser approximation has no npm dependencies. Run its syntax and behavioral contracts with Node.js:

```powershell
node --check .\simulator-engine.js
node --check .\app.js
node --test .\tests\browser_model_contract.test.js
```

Run the default Python API and static-contract suite:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_*.py' -v
```

To opt into a real CasADi reset-and-step integration check:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUN_GREENLIGHT_INTEGRATION = '1'
& '.\.venv\Scripts\python.exe' -B -m unittest tests.test_greenlight_integration -v
```

Project collaboration and validation records are available from [`worklogs/index.html`](worklogs/index.html). The ready-to-copy instructions for setting up another computer are in [`SECOND_COMPUTER_PROMPT.md`](SECOND_COMPUTER_PROMPT.md).

> **Protected research mode:** GreenLight practice and GreenLight 2 source code outside this repository may be loaded read-only, but it must never be modified. Keep `.venv`, downloads, caches, logs, and outputs inside this repository; set `PYTHONDONTWRITEBYTECODE=1` and launch with Python `-B`. Thesis manuscripts, datasets, experiment outputs, and other non-source research artifacts remain out of scope.

## GitHub collaboration

- Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the structured issue forms.
- Use [`MODEL_CARD.md`](MODEL_CARD.md) before interpreting or changing model behavior.
- Report sensitive software problems through [`SECURITY.md`](SECURITY.md), not a public issue.
- Pull requests run a free public-repository CI job containing the default Python contracts and deterministic browser-model tests. It uses no paid API, cache upload, or artifact storage.
- Every completed project task has an English HTML record in [`worklogs/index.html`](worklogs/index.html).

## License status

No open-source software license has been selected yet. Public GitHub visibility does not grant permission to copy, redistribute, or create derivative works. The repository owner must make and document the license decision before broad reuse is invited.

## 繁體中文

這是一個獨立的 GreenLight 2 互動溫室與科學模型橋接器。它不應放在 `greenlight-practice` 或 `GreenLight-Gym2-practice` 裡；後端以唯讀方式載入指定的 GL-Gym2 原始碼，並禁止在 practice 專案產生 Python bytecode。

## 現在直接啟動完整模型

在專案資料夾內，使用自己的 `.venv` 啟動：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B .\server.py --engine glgym
```

開啟 <http://127.0.0.1:4173/>。控制面板右上角應顯示「GreenLight 2 完整模型」。

伺服器模式：

- `--engine glgym`：必須使用完整 GreenLight-Gym2，初始化失敗就停止。
- `--engine auto`：優先使用完整模型；不可用時讓網頁使用瀏覽器近似模型。
- `--engine browser`：只提供網頁與 API 狀態，強制使用瀏覽器近似模型。

## 從乾淨環境重新安裝

使用 Python 3.12，所有環境與下載快取都留在模擬器資料夾：

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --extra greenlight --python 3.12
```

這會安裝 CasADi、NumPy、SciPy、Pandas、Gymnasium、PyYAML 與 pytz，但不會安裝或修改 sibling GL-Gym2 source package；後端會透過 `sys.path` 唯讀載入它。

## 模型與畫面

- 左側 2.5D 溫室會反映：
  - 日夜與阿姆斯特丹實測天氣
  - 屋頂通風窗、保溫幕、遮光幕
  - 補光燈、暖氣管與 CO₂ 注入
  - 冠層、果實乾物質、葉面積與凝結提示
- 右側控制 GreenLight 2 六項絕對開度：
  - `uBoil` 鍋爐加熱
  - `uCO2` CO₂ 注入
  - `uThScr` 保溫幕
  - `uVent` 屋頂通風
  - `uLamp` 補光燈
  - `uBlScr` 遮光幕
- 完整模式直接驅動：
  - 28-state CasADi/CVODES GreenLight 模型
  - 每步 900 秒（15 分鐘）
  - Amsterdam 2008–2012 weather repository
  - GL-Gym2 rule-based controller 或手動 0–1 絕對控制
  - 溫度、RH、CO₂、管道溫度、冠層與作物狀態
  - 能源、CO₂ 與成本累計
- Python 後端停止時，前端會自動暫停並切回瀏覽器近似模型，不會讓播放迴圈卡死。

## API

同源 API，不開放 CORS，預設只綁定 `127.0.0.1`：

- `GET /api/status`
- `POST /api/reset`
- `POST /api/step`

所有 mutation 都有單調遞增的 `revision`；前端傳送 `expectedRevision`，避免多分頁或重複請求互相覆蓋。CasADi 環境由後端鎖定成單一序列操作。

手動 step 範例：

```json
{
  "steps": 1,
  "mode": "manual",
  "controls": {
    "uBoil": 0.35,
    "uCO2": 0.15,
    "uThScr": 0.4,
    "uVent": 0.05,
    "uLamp": 0.25,
    "uBlScr": 0.0
  },
  "targets": {
    "dayTemp": 21.5,
    "nightTemp": 17.5,
    "co2": 900,
    "maxRh": 82
  },
  "expectedRevision": 1
}
```

## 驗證

一般測試：

```powershell
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_*.py' -v
```

實際建構 CasADi 模型並跑一次 reset／step：

```powershell
$env:RUN_GREENLIGHT_INTEGRATION = '1'
& '.\.venv\Scripts\python.exe' -B -m unittest tests.test_greenlight_integration -v
```

## 結構

```text
greenlight-2-simulator/
├─ backend/
│  ├─ greenlight_adapter.py  # 28-state GL-Gym2 adapter
│  └─ server.py              # 靜態伺服器、API、驗證與 revision lock
├─ tests/
│  ├─ test_api_server.py
│  ├─ test_greenlight_integration.py
│  └─ test_static_contract.py
├─ index.html
├─ styles.css
├─ simulator-engine.js       # 瀏覽器安全回退模型
├─ app.js                    # UI、API 偵測與無重疊播放迴圈
├─ server.py
├─ pyproject.toml
└─ uv.lock
```
