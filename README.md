# trim-media-online · 飞牛影视在线能力扩展

给飞牛影视（`trim.media`）增加在线能力：媒体库首页注入 **4 个豆瓣榜单库**（点开即播），
可选为单个资源站生成**独立媒体库**（分类深翻、无限滚动），并在**原生搜索**里聚合
苹果 CMS 资源站的在线影视，用飞牛自带播放器**直接播放**。搜索结果默认**在线前排**。

配套能力一应俱全：

- **跨端可用**：网页 / 手机 App / TV 盒子（8005 TCP 兼容网关）都能看到并播放在线内容；
- **跨端续播**：「继续观看」进度在 Web / iOS / Android / TV 间互通，支持回退与起播抖动保护；
- **收藏与已看**：在线条目可加入收藏夹、标记已看（本地持久化，卸载即清）；
- **真实清晰度**：线路菜单按 ffprobe 实际探测标注 4K / 1080P / 720P，支持画质优先选线；
- **播放去广告**（可选，默认关闭）：实时剥除 m3u8 中的广告分片；
- **弹幕**（可选，自配 danmu_api）：把弹幕转成 **ASS 字幕轨**交给原生播放器渲染。

零侵入、完全可逆：不改官方二进制 / nginx / 数据库，靠 Unix Socket 原子接管
（`renameat2(NOREPLACE)` + fail-closed 自动回滚）。

> 本项目基于 [yujian0815/fnmedia-ext](https://github.com/yujian0815/fnmedia-ext)（MIT License）改造，
> 并参考了 [puermilk/aimimang](https://github.com/puermilk/aimimang) 的设计思路
> （**不内置任何源、全部由使用者自行配置**）。感谢两位上游作者的开源工作。
> 与上游的差异见 [CHANGELOG.md](CHANGELOG.md)。

> ⚠️ **免责声明**：本项目是开源免费的技术研究 / 个人媒体库工具，**本身不提供、不存储、不分发任何影视、图片或播放地址，也不内置任何资源站点信息**；所有在线内容均来自使用者自行配置的第三方接口与公开榜单，版权归原权利人所有。本项目**不提供、不推荐、不解答任何资源站点的名称、地址或获取方法**，接口由使用者自行添加并自行核实合法性。仅供学习交流与个人合法观看自有 / 已授权内容，请勿商用或传播侵权内容；由此产生的法律责任由使用者自行承担。

## 装完第一件事：添加你的源

本项目**不内置任何资源站线路**。安装后请打开管理页，在「资源站」页添加你自行获取的
苹果 CMS V10 标准 JSON 接口：

```
https://站点地址/api.php/provide/vod/at/json
```

返回 `{"code":1,"list":[{vod_name, vod_play_url, ...}]}` 即被识别。添加后可用
「测试 / 全部测速」验证连通性（耗时、命中条数、直链数），也可在「资源站」页下方
「订阅同步」从 LunaTV 配置定时拉取。请只接入你有权访问的接口。

### 订阅同步：LunaTV 定时拉源 + 测速（可选）

「资源站」页下方的「订阅同步」提供 **LunaTV 定时同步**：从公开的
[`hafrey1/LunaTV-config`](https://github.com/hafrey1/LunaTV-config) 拉取现成的苹果 CMS
源清单，自动去重、逐个测速、可用源自动入库。

| 预设 | 说明 |
|---|---|
| 精简版 `jin18` | 仅普通内容，源少而精（推荐） |
| 精简+ `jingjian` | 在精简版基础上补充更多源（含成人源） |
| 完整版 `full` | 仓库当前全部源 |

- 也可粘贴任意 LunaTV / MoonTV 配置地址（JSON、Base58 或 Base64 编码的 `.txt` 订阅）。
- **定时同步**：开启后按设定间隔（默认 12 小时）自动拉取并测速；点「立即同步」可随时手动执行，手动选择的预设/地址会保存为定时任务配置。
- **测速**：每源请求一次苹果 CMS `ac=detail`，记录延迟、结果数与连续失败次数，按延迟排序展示；新源只有测速通过才入库。
- **死源自动禁用**：连续两轮测速失败的源自动停用（管理台可见、可随时恢复）；整轮大面积失败（如断网）时自动跳过禁用，避免误伤。
- 抓取走「资源站」页下方「订阅同步」配置的**订阅 / API 中转代理**：支持 HTTP 正向代理（`http://user:pass@host:port`）和 CORSAPI 式 URL 前缀中转（自动拼 `?url=原地址`）。中转作用于配置拉取与源 API（测速/搜索/分类），**媒体播放仍直连**；未配置时 GitHub 直连失败会自动尝试国内镜像。
- 该功能只同步第三方清单，**源的可用性与合法性由使用者自行核实**。

未配置源时：在线搜索与热门榜单均无内容；本地媒体库不受任何影响。

## 适配版本

| 项目 | 已验证 / 要求 |
|---|---|
| fnOS | **1.2.0 及以上**（FPK manifest 最低要求） |
| 官方影视应用 | **trim.media `0.9.8-1`**（上游实测） |
| TV / 盒子端 | 需内核支持 nftables；通过 8005 TCP 兼容网关接入（默认开启） |
| CPU 架构 | `all`（纯 Python，安装时创建独立 venv） |
| 安装方式 | fnOS 应用中心手动安装 FPK，可安装在 `/vol1`、`/vol2` 等数据卷 |
| 依赖 | 官方「影视 (trim.media)」必须保持安装并启用 |
| 网络 | 资源站 JSON API 默认直连（不读取系统代理环境变量）；配置中转后，配置拉取与源 API 经中转，媒体流仍直连 |

> 未来若 fnOS / trim.media 升级后签名常量或接口结构变化，停用扩展会立即恢复官方服务，等待新版本适配。

## 下载安装

1. 打开 [Releases](https://github.com/alec1314/trim-media-online/releases)，下载最新的 `trim-media-online-<version>.fpk`。
2. 在 fnOS **应用中心 → 手动安装 FPK** 中选择该文件，安装向导需勾选同意《免责声明》。
3. 选择应用安装所在存储卷，保持依赖应用 **影视 (trim.media)** 为运行状态。
4. 安装完成后启用「trim-media-online」，桌面/应用内会出现 **在线扩展管理**。
5. 管理页添加资源站接口后，打开官方「影视」，直接搜索中文片名即可看到带 `【在线】` 标记的结果。

管理入口为应用内 iframe：`/app/trim-media-online/`（桌面网关同源转发）；
旧的直连路径 `/v/online-admin` 仍保留。卸载或停用扩展会自动把
`/var/run/trim_media.sock` 还原给官方影视服务。

> ⚠️ 不要与上游 fnmedia-ext / 爱迷茫等同类接管应用同时启用——它们争抢同一个官方 socket，只能二选一。

## 工作原理

```
浏览器/飞牛App ── nginx(/v) ─────────────────┐
桌面入口 ── /app/trim-media-online ──────────┤
                                            ├─→ /var/run/trim_media.sock
TV / 盒子 ── TCP 8005 ── nftables → 18005 ───┘
                                                     │
                                                     ▼
                                          trim-media-online(FastAPI)
                                            ├─ 普通请求 → 透传官方后端(upstream socket)
                                            ├─ /search/list → 注入在线结果（默认排最前）+ 本地结果
                                            ├─ /item /season/* /episode/* /play/* /stream/* → 伪造链路
                                            ├─ mediadb/list · mediadb/sum · item/list · item/<guid>
                                            │      → 注入豆瓣榜单四库 + 单源独立库（可选）
                                            └─ /v/media/online/* → HLS/分片/密钥/mp4 反向代理
```

### TV / 盒子端

飞牛影视 TV 端与部分第三方客户端会直连影视服务的 **8005 TCP 端口**，不经过 nginx 的
`/v`，因此只接管 UDS 时这些客户端看不到在线内容。安装后扩展会：

1. 在本机 `18005` 启动一个 TCP 网关，把连接转发到已接管的代理 UDS；
2. 用 nftables 把入站 `8005` 重定向到该网关（IPv4 + IPv6）；
3. 服务停止/卸载时自动撤销重定向，8005 立即回落到官方服务（fail-open）。

网页端、手机端仍走原 `/v` 链路，不受影响。若与旁路由 / 端口转发规则冲突，可在
systemd 单元中设置环境变量 `TMO_TV_COMPAT=0` 关闭该能力（TV 端将恢复为仅官方内容）。

## 功能

### 热门榜单媒体库（展示 / 播放解耦）

- **展示层（真实榜单）**：后台定时（默认每 6 小时）拉取豆瓣周榜 + 豆瓣官方 tag 推荐，
  合成 4 个虚拟库 **🎬热门电影 / 📺热门剧集 / 🌸动漫新番 / 🎤热门综艺**（合计上限与
  每库条数可在管理台调整），含豆瓣海报、评分、年份、简介；原子缓存，媒体库只读、秒开。
- **播放层（按需解析）**：榜单条目点进详情时才用片名实时聚合搜索你配置的资源站，
  命中后挂载可播放 brief，复用详情/选集/多线路/续播/代理播放链；源站没有的返回
  「暂无在线片源」。
- **严格同名匹配**：榜单片与资源站结果的绑定要求归一化片名严格相等，搜不到同名源
  就如实显示「暂无在线片源」——**宁可不显示也不串片**（点开 A 片播出 B 片属永久禁止的回归）。
- 豆瓣图床经海报代理并带 Referer，失败回退内联 SVG；兼容官方分页、排序参数；库卡可置顶。

### 单源独立媒体库（可选）

在「资源站」页给某个源勾选「独立库」，即为该源单独生成一张媒体库卡片：

- 定期拉取该源苹果 CMS 分类表 `ac=list`，叶子子类归并为电影 / 剧集 / 动漫 / 综艺。
- 浏览时按页直连 `ac=detail&t=<子类id>&pg=N`（详情自带播放地址，**点开即播**）；页级缓存 + 多叶子并发合并去重，容忍慢源抖动。
- 适配官方前端**虚拟列表无限滚动**：全局偏移跨页取窗 + 去重，保证滚动连续。

### 搜索 / 选集 / 多线路 / 续播

- 搜索把不同资源站命中的同一部片**聚合为一个条目**，每个资源站一条线路；播放设置里的
  清晰度菜单即线路菜单，卡顿/失效时即时换源。聚合结果按 guid 去重。
- 单集渲染为 Movie（点开即播），多集渲染为 TV，走飞牛原生选集接口；集身份与线路解耦。
- **跨端搜索**：识别 Web / 手机 / TV 各端的参数习惯（`q` / `keyword` / `kw` / `wd`、
  GET / POST），并按端规整响应模型（Flutter / TV 端解析严格）。
- **跨端续播**：在线播放进度落在本地 `state/history.json`，与官方本地历史合并进
  「继续观看」；Web / iOS / TV 上报口径不同，统一反查归一到同一集；进度以最后一次上报
  为准（可回退），仅保护进入播放页时的 ts=0，起播抖动不会覆盖已有进度。
- HLS 源经自研代理重写分片/密钥 URI（透传 Referer/UA/Range），mp4 直链流式反代支持拖动。
- **播放流畅度**：起播并行竞速选最快线并短时记忆；点击即后台预热播放列表；起播成功预热
  同线路下一集；HLS 分片预取缓存（Range 请求同样命中）；坏线短时跳过并自动换线。
- **搜索提速**：跳过死亡/失败冷却中的源、并发限流、软截止（到点先返回已完成源的结果）、
  单源超时预算，榜单点详情与搜索框共享 2 分钟结果缓存。
- **网页嗅探**：部分源的线路给的是「播放页 URL」而非直链，内置嗅探引擎用纯 HTTP +
  正则/JSON 解析还原真实 m3u8/mp4 地址，无需安卓模拟器。

### 收藏与已看标记

官方后端不认识虚拟在线 guid，收藏 / 已看接口会直接报错。扩展在本地接管这两类标记
（`state/marks.json`），并回填到 `item/list`、`item/{guid}`、`favorite/list`，
让官方收藏夹和「已看」筛选对在线内容照常可用；卸载即清、零数据库污染。

### 线路清晰度标注与画质优先

各采集源的线路名（拼音缩写等）本身常不含清晰度。扩展在拿到**真实可播地址**后用
ffprobe 探测实际分辨率（HLS 取首个真实 TS 分片、mp4 Range 拉前 2MB 读 moov），
给线路名追加 **4K / 1080P / 720P** 标注；管理台可开启「画质优先」选线
（`prefer_quality_source`）。探测失败/超时一律静默跳过，绝不影响播放。

### 电视 / 手机端起播优化

- **线路菜单精简**（默认开启，管理台「资源站 → 播放线路」可关）：TV / 手机原生播放器
  拿到多线路清单后会逐条串行预取，慢线累加等待导致起播慢。现在对这些端只下发当前线路，
  其余线路由服务端提前并发备好（切菜单即时命中）；**网页版仍是完整菜单**，可手动切线。
- 飞牛各端（Web / Flutter / TV）的反序列化严格度差异极大，服务端按 User-Agent
  识别客户端画像（client profile），对响应做按端裁剪与规整。

### 播放去广告（可选，默认关闭）

管理台「弹幕」页的「播放去广告」卡片，勾选并保存后生效：

- 播放在线片时实时分析当前线路的 m3u8，剥除片头/片中常见的广告分片。
- 只用**同步规则**（分片地址广告特征、成群超短分片、CDN 短段切换），
  **不在起播路径新增任何网络请求**，不改变选线与竞速行为。
- 宁可漏删不可误删：判断不确定就保留原片；单次删除量超过总分片数 30%
  时整表放弃；主播放列表绝不处理；删除后输出仍是标准 m3u8。
- 关闭时播放链路与之前完全一致。

### 弹幕（可选，自配 danmu_api）

飞牛影视播放器没有独立弹幕层，但 Web 端播放器内置了 **JASSUB（libass）外挂字幕渲染**，
支持 ASS 的 `\move` 动画。本扩展据此把弹幕转成 ASS 字幕轨，以「弹幕」外挂字幕的形式
交给原生播放器渲染——不修改播放器、不另起播放页：

1. 自行部署 [danmu_api](https://github.com/huangxd-/danmu_api)（弹弹play 兼容接口），
   本地 Docker 示例：`docker run -d -p 9321:9321 -e TOKEN=87654321 --name danmu-api logvar/danmu-api:latest`；
2. 打开管理台「弹幕」页，填写接口地址，启用并保存：
   - 本地 Docker：`http://NAS地址:9321`
   - **Cloudflare Workers**：`https://<你的worker>.workers.dev`
   - **Vercel / Netlify**：填部署后的完整域名
   - 自定义 Token 无需手写路径，程序会自动拼成 `/{TOKEN}/api/v2/...`；
     漏写协议时，公网域名自动用 `https://`，内网地址自动用 `http://`。
3. 播放在线影片时，字幕菜单会出现「弹幕」（默认自动选中）；按片名 + `SxxEyy`
   自动匹配，冷门片或命名不规范的片源可能匹配不到，可在管理台调整时间偏移。

> **Cloudflare Workers 部署注意**：danmu_api 的 CF 版本接口路径与 Docker 完全一致，
> 支持 `/api/v2/match`（POST）、`/api/v2/comment/{id}`、`/api/v2/search/episodes`。
> 但官方也提示 CF 部署偏不稳定：B 站源可能被风控、单次请求子请求数有上限
> （长视频后半段弹幕可能缺失）。另外 Workers 域名在部分网络下不可达，建议绑定自定义域名；
> 追求稳定体验优先本地 Docker 或 Vercel/Netlify。
> danmu_api 默认限流 `RATE_LIMIT_MAX_REQUESTS=3`（每分钟同 IP），匹配失败较多时
> 可在 Worker 环境变量中调大或设为 `0` 关闭。

说明与边界：

- 本项目**不内置、不代理、不分发**任何弹幕服务或弹幕内容，接口由使用者自行部署与配置；
  弹幕版权归原平台/用户所有，请遵守对应服务条款。
- 接口不可用、匹配失败或超时只会得到空字幕，**不影响正片播放**。
- 受播放器能力限制：没有独立弹幕开关/屏蔽词/透明度面板，字号与样式由字幕渲染统一控制；
  TV 端与手机端能否渲染 ASS 外挂字幕取决于客户端实现，以实际表现为准。
- 弹幕数据缓存 6 小时（失败 10 分钟），同一集重复播放不会反复请求接口。

## 目录

```
proxy/
  app.py            主代理：透传 + 搜索注入 + 播放伪造 + HLS/海报代理 + 管理 API
  supervise.py      原子接管守护（暂存启动→校验→换名；退出自动回滚）
  tcp_gateway.py    TV / 盒子端 8005 TCP 兼容网关
  webui_gateway.py  桌面应用网关（/app/trim-media-online 同源转发）
  providers.py      苹果CMS V10 适配 + 连通性探测（不内置任何源，全部用户配置）
  sniff.py          网页嗅探引擎：播放页 URL → 真实媒体地址（纯 HTTP，无需模拟器）
  inject.py         在线条目 → 飞牛 item/stream/play/history 结构
  client.py         客户端画像：按 User-Agent 识别 Web / Flutter / TV 端并适配响应
  store.py          标题/线路持久化、跨源聚合、按集解析、线路/集反查索引
  charts.py         豆瓣榜单刷新与虚拟热门四库
  catalog.py        单源独立媒体库（分类深翻、无限滚动）
  history.py        在线播放进度（继续观看，跨端归一）
  marks.py          在线条目本地收藏 / 已看标记
  quality.py        线路实际分辨率探测（ffprobe）与 4K/1080P/720P 标注
  danmu.py          弹幕：danmu_api → ASS 字幕轨
  adfilter.py       m3u8 播放去广告（同步规则，起播零开销）
  subfetch.py       订阅 / API 抓取低层工具（HTTP 正向代理 / URL 前缀中转、curl_cffi 指纹）
  lunatv.py         LunaTV / MoonTV 配置拉取与解析（JSON / Base58 / Base64）
  sourcehealth.py   源健康画像（成功率/延迟/死亡冷却，搜索与播放共用）
  config.py         可热加载配置：源增删、启用开关、噪音过滤、LunaTV 定时同步
  features.py       可选特性开关（本仓库为公开构建，专有特性代码不在仓库内）
  admin_ui.py       单文件管理页（概览 / 资源站与订阅 / 弹幕 / 搜索 / 关于）
tests/              unittest 测试集（见下）
deploy/             持久 systemd 单元 + install/uninstall
packaging/fpk/      飞牛应用中心 FPK 打包
wheelhouse/         离线依赖 wheels（弱网安装用）
state/              config.json / titles.json / history.json / marks.json（运行时生成）
```

## 测试

```
python3 -m unittest discover tests -v
```

覆盖播放链路回归、去广告安全边界（不确定就不删）、榜单绑定严格同名匹配、
TV/手机线路菜单精简与预热、管理 API 兼容性（带应用中心前缀）等场景；
用 mock 隔离外部网络，不依赖真实资源站。

## 从源码构建 FPK

```
git clone https://github.com/alec1314/trim-media-online.git
cd trim-media-online
bash packaging/fpk/build.sh
# 产物：dist/trim-media-online-<version>.fpk（附 .sha256）
```

打包脚本在缺少 `fnpack` 时会自动从飞牛官方 CDN 下载。

## 管理 API（节选）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/v/api/ext/status` | 运行状态 + 配置 |
| GET | `/v/api/ext/source-health` | 源健康画像（成功率/延迟/状态） |
| POST | `/v/api/ext/source/add` | `{name,api}` 添加自定义源（按地址去重） |
| POST | `/v/api/ext/source/delete` | `{id}` 删除源 |
| POST | `/v/api/ext/source/test` / `test-all` | 单源 / 全部连通性探测 |
| POST | `/v/api/ext/source/standalone` | `{id,enabled}` 开关单源独立库 |
| POST | `/v/api/ext/source/priority` | 源优先级（画质优先/线路排序） |
| POST | `/v/api/ext/source/restore` | 清空全部源（回到初始状态） |
| GET | `/v/api/ext/lunatv/status` | LunaTV 定时同步状态 |
| POST | `/v/api/ext/lunatv/sync` | 立即执行 LunaTV 拉源同步 |
| POST | `/v/api/ext/subscription-proxy` | 配置订阅 / API 中转代理 |
| POST | `/v/api/ext/danmu/test` | 弹幕接口连通性 + 真实匹配探测 |
| POST | `/v/api/ext/hot/refresh` | 立即刷新豆瓣榜单缓存 |
| POST | `/v/api/ext/lib/pin` | 置顶 / 取消置顶媒体库卡片 |
| POST | `/v/api/ext/junk-keywords` | 搜索噪音关键词过滤 |
| POST | `/v/api/ext/config` | 保存管理台配置 |

## 已知限制

- TV 端兼容依赖 nftables 把入站 8005 重定向到本机网关；若使用旁路由/端口转发，请确保 8005 未被其他规则提前 DNAT。
- 弹幕依赖播放器自带的 ASS 外挂字幕渲染（Web 端 JASSUB/libass），无独立弹幕层；TV/手机端以实际表现为准，详见上方「弹幕」。
- 点播源随时间失效，本扩展不做转存/STRM 落库——即刷即播、即搜即播；失效源在管理页删除或替换。
- 榜单片与搜索结果聚合均按「归一化片名严格相等」绑定，年份不作硬门槛（大量苹果 CMS 源不返回年份）；极少数纯重名不同作品可能被并为一体。
- 官方 trim.media 升级若改动接口结构需相应适配；停用即恢复官方服务。

## 致谢

- [yujian0815/fnmedia-ext](https://github.com/yujian0815/fnmedia-ext)：本项目直接基座（MIT）。
- [puermilk/aimimang](https://github.com/puermilk/aimimang)：不内置源、纯用户配置的产品思路参考。
- [LibreSpark/LibreTV](https://github.com/LibreSpark/LibreTV)：榜单展示/播放解耦设计参考。
- [SzeMeng76/LunaTV](https://github.com/SzeMeng76/LunaTV)：HLS 分片预取与弹幕生态参考。
- [huangxd-/danmu_api](https://github.com/huangxd-/danmu_api)：弹弹play 兼容弹幕接口。
- 飞牛 fnOS 平台与开源社区。

## 许可证

[MIT](LICENSE)。上游 fnmedia-ext 与本项目的贡献者版权信息见 LICENSE 文件头。
