# trim-media-online · 飞牛影视在线能力扩展

给飞牛影视（`trim.media`）增加在线能力：媒体库首页注入 **4 个豆瓣榜单库**（点开即播），可选为单个资源站生成**独立媒体库**（分类深翻、无限滚动），并在**原生搜索**里聚合苹果 CMS 资源站的在线影视，用飞牛自带播放器**直接播放**。搜索结果默认**在线前排**。可选接入自建弹幕接口（danmu_api），把弹幕转成 **ASS 字幕轨**交给原生播放器渲染。

零侵入、完全可逆：不改官方二进制 / nginx / 数据库，靠 Unix Socket 原子接管（`renameat2(NOREPLACE)` + fail-closed 自动回滚）。

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

返回 `{"code":1,"list":[{vod_name, vod_play_url, ...}]}` 即被识别。添加后可用「测试 / 全部测速」验证连通性（耗时、命中条数、直链数），也可在「订阅同步」页从 LunaTV 配置定时拉取。请只接入你有权访问的接口。

### 订阅同步：LunaTV 定时拉源 + 测速（可选）

「订阅同步」页提供 **LunaTV 定时同步**：从公开的
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
- 抓取走「订阅同步」页配置的**订阅 / API 中转代理**：支持 HTTP 正向代理（`http://user:pass@host:port`）和 CORSAPI 式 URL 前缀中转（如 `https://ac9.cc.cd/`，自动拼 `?url=原地址`）。中转作用于配置拉取与源 API（测速/搜索/分类），**媒体播放仍直连**；未配置时 GitHub 直连失败会自动尝试国内镜像。
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
| 网络 | 资源站 JSON API 默认直连（`trust_env=False`，不读取系统代理环境变量）；配置中转后，配置拉取与源 API 经中转，媒体流仍直连 |

> 未来若 fnOS / trim.media 升级后签名常量或接口结构变化，停用扩展会立即恢复官方服务，等待新版本适配。

## 下载安装

1. 打开 [Releases](https://github.com/alec1314/trim-media-online/releases)，下载最新的 `trim-media-online-<version>.fpk`。
2. 在 fnOS **应用中心 → 手动安装 FPK** 中选择该文件，安装向导需勾选同意《免责声明》。
3. 选择应用安装所在存储卷，保持依赖应用 **影视 (trim.media)** 为运行状态。
4. 安装完成后启用「trim-media-online」，桌面/应用内会出现 **在线扩展管理**。
5. 管理页添加资源站接口后，打开官方「影视」，直接搜索中文片名即可看到带 `【在线】` 标记的结果。

管理入口为应用内 iframe：`/app/trim-media-online/`；旧的直连路径 `/v/online-admin` 仍保留。卸载或停用扩展会自动把 `/var/run/trim_media.sock` 还原给官方影视服务。

> ⚠️ 不要与上游 fnmedia-ext / 爱迷茫等同类接管应用同时启用——它们争抢同一个官方 socket，只能二选一。

## 工作原理

```
浏览器/飞牛App ── nginx(/v) ─────────────────┐
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

### 弹幕（可选，自配 danmu_api）

飞牛影视播放器没有独立弹幕层，但 Web 端播放器内置了 **JASSUB（libass）外挂字幕渲染**，
支持 ASS 的 `\move` 动画。本扩展据此把弹幕转成 ASS 字幕轨，以「弹幕」外挂字幕的形式
交给原生播放器渲染——不修改播放器、不另起播放页：

1. 自行部署 [danmu_api](https://github.com/huangxd-/danmu_api)（弹弹play 兼容接口），
   例如：`docker run -d -p 9321:9321 -e TOKEN=87654321 --name danmu-api logvar/danmu-api:latest`；
2. 打开管理台「弹幕」页，填写接口地址（如 `http://NAS地址:9321`），启用并保存；
3. 播放在线影片时，字幕菜单会出现「弹幕」（默认自动选中）；按片名 + `SxxEyy`
   自动匹配，冷门片或命名不规范的片源可能匹配不到，可在管理台调整时间偏移。

说明与边界：

- 本项目**不内置、不代理、不分发**任何弹幕服务或弹幕内容，接口由使用者自行部署与配置；
  弹幕版权归原平台/用户所有，请遵守对应服务条款。
- 接口不可用、匹配失败或超时只会得到空字幕，**不影响正片播放**。
- 受播放器能力限制：没有独立弹幕开关/屏蔽词/透明度面板，字号与样式由字幕渲染统一控制；
  TV 端与手机端能否渲染 ASS 外挂字幕取决于客户端实现，以实际表现为准。
- 弹幕数据缓存 6 小时（失败 10 分钟），同一集重复播放不会反复请求接口。

### 热门榜单媒体库（展示 / 播放解耦）

- **展示层（真实榜单）**：后台定时（默认每 6 小时）拉取豆瓣周榜 + 豆瓣官方 tag 推荐，合成 4 个虚拟库 **🎬热门电影 / 📺热门剧集 / 🌸动漫新番 / 🎤热门综艺**，每库最多 160 部，含豆瓣海报、评分、年份、简介；原子缓存，媒体库只读、秒开。
- **播放层（按需解析）**：榜单条目点进详情时才用片名实时聚合搜索你配置的资源站，命中后挂载可播放 brief，复用详情/选集/多线路/续播/代理播放链；源站没有的返回「暂无在线片源」。
- 豆瓣图床经海报代理并带 Referer，失败回退内联 SVG；兼容官方分页、排序参数。

### 单源独立媒体库（可选）

在「资源站」页给某个源勾选「独立库」，即为该源单独生成一张媒体库卡片：

- 定期拉取该源苹果 CMS 分类表 `ac=list`，叶子子类归并为电影 / 剧集 / 动漫 / 综艺。
- 浏览时按页直连 `ac=detail&t=<子类id>&pg=N`（详情自带播放地址，**点开即播**）；页级缓存 + 多叶子并发合并去重，容忍慢源抖动。
- 适配官方前端**虚拟列表无限滚动**：全局偏移跨页取窗 + 去重，保证滚动连续。

### 搜索 / 选集 / 多线路 / 续播

- 搜索把不同资源站命中的同一部片聚合为一个条目，每个资源站一条线路；播放设置里的清晰度菜单即线路菜单，卡顿/失效时即时换源。
- 单集渲染为 Movie（点开即播），多集渲染为 TV，走飞牛原生选集接口；集身份与线路解耦。
- 在线播放进度落在本地 `state/history.json`，与官方本地历史合并进「继续观看」，支持跨源续播。
- HLS 源经自研代理重写分片/密钥 URI（透传 Referer/UA/Range），mp4 直链流式反代支持拖动。
- 播放流畅度：起播并行竞速选最快线并短时记忆；点击即后台预热播放列表；起播成功预热同线路下一集；坏线短时跳过并自动换线；已知失效线路全网回源（按片名）。
- 搜索提速：跳过死亡/失败冷却中的源、限制并发、单源超时预算（普通 8s / 回源 6s），榜单点详情与搜索框共享 2 分钟结果缓存。

## 目录

```
proxy/
  app.py            主代理：透传 + 搜索注入 + 播放伪造 + HLS/海报代理 + 管理 API
  supervise.py      原子接管守护（暂存启动→校验→换名；退出自动回滚）
  providers.py      苹果CMS V10 适配 + 连通性探测（不内置任何源，全部用户配置）
  inject.py         在线条目 → 飞牛 item/stream/play/history 结构
  store.py          标题/线路持久化、跨源聚合、按集解析、线路/集反查索引
  charts.py         豆瓣榜单刷新与虚拟热门四库
  catalog.py        单源独立媒体库（分类深翻、无限滚动）
  history.py        在线播放进度（继续观看）
  config.py         可热加载配置：源增删、启用开关、噪音过滤、LunaTV 定时同步
  lunatv.py         LunaTV / MoonTV 配置拉取与解析（JSON / Base58 / Base64）
  sourcehealth.py   源健康画像（成功率/延迟/死亡冷却，搜索与播放共用）
  adfilter.py       选集引流广告过滤（只做名称判断）
  admin_ui.py       单文件管理页（源管理 / 测速 / 订阅同步 / 设置）
deploy/             持久 systemd 单元 + install/uninstall
packaging/fpk/      飞牛应用中心 FPK 打包
wheelhouse/         离线依赖 wheels（弱网安装用）
state/              config.json / titles.json / history.json（运行时生成）
```

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
| POST | `/v/api/ext/source/add` | `{name,api}` 添加自定义源（按地址去重） |
| POST | `/v/api/ext/source/delete` | `{id}` 删除源 |
| POST | `/v/api/ext/source/restore` | 清空全部源（回到初始状态） |
| POST | `/v/api/ext/source/test` / `test-all` | 单源 / 全部连通性探测 |
| POST | `/v/api/ext/hot/refresh` | 立即刷新豆瓣榜单缓存 |

## 已知限制

- TV 端兼容依赖 nftables 把入站 8005 重定向到本机网关；若使用旁路由/端口转发，请确保 8005 未被其他规则提前 DNAT。
- 飞牛原生播放器没有弹幕层，暂不提供在线弹幕；可行方案见下方「关于弹幕」。
- 点播源随时间失效，本扩展不做转存/STRM 落库——即刷即播、即搜即播；失效源在管理页删除或替换。
- 多线路聚合按「片名规范化 + 年份」判定，极少数同名不同作品可能被并为一体。
- 官方 trim.media 升级若改动接口结构需相应适配；停用即恢复官方服务。

## 致谢

- [yujian0815/fnmedia-ext](https://github.com/yujian0815/fnmedia-ext)：本项目直接基座（MIT）。
- [puermilk/aimimang](https://github.com/puermilk/aimimang)：不内置源、纯用户配置的产品思路参考。
- [LibreSpark/LibreTV](https://github.com/LibreSpark/LibreTV)：榜单展示/播放解耦设计参考。
- 飞牛 fnOS 平台与开源社区。

## 许可证

[MIT](LICENSE)。上游 fnmedia-ext 与本项目的贡献者版权信息见 LICENSE 文件头。
