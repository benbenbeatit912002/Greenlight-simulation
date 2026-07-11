# GreenLight 2 溫室模擬器

獨立的 GreenLight 2 互動溫室與科學模型橋接器：

```text
C:\Project\greenlight-project\greenlight-2-simulator
```

它不在 `greenlight-practice` 或 `GreenLight-Gym2-practice` 裡。後端以唯讀方式載入同層的 GL-Gym2 原始碼，並禁止在 practice 專案產生 Python bytecode。

## 現在直接啟動完整模型

依賴已安裝在本資料夾自己的 `.venv`：

```powershell
cd C:\Project\greenlight-project\greenlight-2-simulator
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

