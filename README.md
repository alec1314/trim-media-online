# trim-media-online · 飞牛影视在线能力扩展

给飞牛影视（`trim.media`）增加在线能力：媒体库首页注入 **4 个豆瓣榜单库 + 4 个资源站海量分类库**（无限滚动、点开即播），并在**原生搜索**里聚合苹果 CMS 资源站的在线影视，用飞牛自带播放器**直接播放**。搜索结果默认**在线前排**。

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

返回 `{"code":1,"list":[{vod_name, vod_play_url, ...}]}` 即被识别。添加后可用「测试 / 全部测速」验证连通性（耗时、命中条数、直链数），也可用左侧「导入订阅」从 TVBox 配置批量导入。请只接入你有权访问的接口。

未配置源时：在线搜索、热门榜单四库、海量分类四库均无内容；本地媒体库不受任何影响。

## 适配版本

| 项目 | 已验证 / 要求 |
|---|---|
| fnOS | **1.2.0 及以上**（FPK manifest 最低要求） |
| 官方影视应用 | **trim.media `0.9.8-1`**（上游实测） |
| CPU 架构 | `all`（纯 Python，安装时创建独立 venv） |
| 安装方式 | fnOS 应用中心手动安装 FPK，可安装在 `/vol1`、`/vol2` 等数据卷 |
| 依赖 | 官方「影视 (trim.media)」必须保持安装并启用 |
| 网络 | 资源站访问使用直连（`trust_env=False`），不读取代理环境变量 |

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
浏览器/飞牛App → nginx(/v) → /var/run/trim_media.sock → trim-media-online(FastAPI)
                                                   ├─ 普通请求 → 透传官方后端(upstream socket)
                                                   ├─ /search/list → 注入在线结果（默认排最前）+ 本地结果
                                                   ├─ /item /season/* /episode/* /play/* /stream/* → 伪造链路
                                                   ├─ mediadb/list · mediadb/sum · item/list · item/<guid>
                                                   │      → 注入豆瓣榜单四库 + 资源站海量分类四库（无限滚动）
                                                   └─ /v/media/online/* → HLS/分片/密钥/mp4 反向代理
```

### 热门榜单媒体库（展示 / 播放解耦）

- **展示层（真实榜单）**：后台定时（默认每 6 小时）拉取豆瓣周榜 + 豆瓣官方 tag 推荐，合成 4 个虚拟库 **🎬热门电影 / 📺热门剧集 / 🌸动漫新番 / 🎤热门综艺**，每库最多 160 部，含豆瓣海报、评分、年份、简介；原子缓存，媒体库只读、秒开。
- **播放层（按需解析）**：榜单条目点进详情时才用片名实时聚合搜索你配置的资源站，命中后挂载可播放 brief，复用详情/选集/多线路/续播/代理播放链；源站没有的返回「暂无在线片源」。
- 豆瓣图床经海报代理并带 Referer，失败回退内联 SVG；兼容官方分页、排序参数。

### 海量分类片库（无限滚动）

额外注入 4 个海量库 **🎞海量电影 / 📺海量剧集 / 🌸海量动漫 / 🎤海量综艺**：

- 定期拉取各资源站苹果 CMS 分类表 `ac=list`，全部子分类按名称归并四大类，自动剔除脏类。
- 浏览时按页直连 `ac=detail&t=<子类id>&pg=N`（每页 20 条、详情自带播放地址，**点开即播**）；页级缓存 + 规范源失败自动换源。
- 适配官方前端**虚拟列表无限滚动**：全局偏移跨 CMS 页取窗 + 会话级去重，保证滚动连续、每部片全局只出现一次。

### 搜索 / 选集 / 多线路 / 续播

- 搜索把不同资源站命中的同一部片聚合为一个条目，每个资源站一条线路；播放设置里的清晰度菜单即线路菜单，卡顿/失效时即时换源。
- 单集渲染为 Movie（点开即播），多集渲染为 TV，走飞牛原生选集接口；集身份与线路解耦。
- 在线播放进度落在本地 `state/history.json`，与官方本地历史合并进「继续观看」，支持跨源续播。
- HLS 源经自研代理重写分片/密钥 URI（透传 Referer/UA/Range），mp4 直链流式反代支持拖动；流层内置去广告。

## 目录

```
proxy/
  app.py            主代理：透传 + 搜索注入 + 播放伪造 + HLS/海报代理 + 管理 API
  supervise.py      原子接管守护（暂存启动→校验→换名；退出自动回滚）
  providers.py      苹果CMS V10 适配 + 连通性探测（不内置任何源，全部用户配置）
  inject.py         在线条目 → 飞牛 item/stream/play/history 结构
  store.py          标题/线路持久化、跨源聚合、按集解析、线路/集反查索引
  charts.py / hot.py  豆瓣榜单刷新与虚拟热门四库
  catalog.py        海量分类四库（无限滚动窗口取数）
  history.py        在线播放进度（继续观看）
  config.py         可热加载配置：源增删、启用开关、噪音过滤、在线前排
  tvbox.py          TVBox 订阅导入（采集接口 + csp/drpy 扩展源）
  admin_ui.py       单文件管理页（源管理/测速/设置）
  updater.py        自更新（GitHub Releases）
  fnmedia_authx.py  官方 authx 签名客户端（MD5 + apiKey）
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
