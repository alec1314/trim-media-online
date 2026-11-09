# 更新日志（trim-media-online）

## 1.0.0（2026-11-09）

首个发布版本。

trim-media-online 基于 [yujian0815/fnmedia-ext](https://github.com/yujian0815/fnmedia-ext) v0.2.43（MIT License）改造而来，
继承其全部核心能力，并做如下调整：

### 变更

- **不内置任何资源站线路**：上游自带的 11 条默认采集线路全部移除。
  所有苹果 CMS V10 采集接口均需使用者在管理页自行添加/启用，
  或通过「导入订阅」从 TVBox 配置批量导入。管理页在未配置源时显示引导提示。
- **「恢复内置源」改为「清空全部源」**：因无内置源，该按钮语义调整为清空全部已配置源（需二次确认）。
- **项目更名**：应用包名 `trim-media-online`，systemd 服务 `trim-media-online.service`，
  运行时目录 `/run/trim-media-online`，桌面网关 `/app/trim-media-online/`。
- 自更新检查指向本仓库 Releases（需在 `proxy/updater.py` 的 `REPO_SLUG` 填入实际 GitHub 仓库）。

### 继承自上游的核心能力（未改动）

- 零侵入可逆接管：Unix Socket 原子换名（`renameat2(NOREPLACE)`），fail-closed 自动回滚
- 原生搜索聚合在线结果（默认前排）、多线路切换、选集（原生 TV UI）、播放记录与智能续播
- 豆瓣热门榜单四库（展示/播放解耦，点开详情时按需搜源）
- 资源站海量分类四库（虚拟列表无限滚动，全局去重）
- m3u8/mp4 反向代理（分片/密钥重写、Range 直通、流层去广告）
- 应用内管理页：源管理、测速、噪音词、源健康画像、片源质量优先级
- TVBox 订阅导入（采集接口 + csp/drpy 扩展源）

上游完整开发历史见 [CHANGELOG-upstream.md](CHANGELOG-upstream.md)。
