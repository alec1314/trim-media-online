#!/usr/bin/env python3
"""飞牛影视·在线扩展 管理台（单文件 HTML，无外部依赖）。

布局对齐 fnmusic-ext 管理台：桌面左侧导航 + 移动端底部导航，多页卡片。
完整版专属区块用可剥离标记包裹，公开构建会被打包脚本整块移除。
"""

ADMIN_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>trim-media-online 管理台</title>
<style>
:root{
  --bg:#f4f6f8;--card:#fff;--line:#e3e8ee;--text:#1c2733;--muted:#68788a;
  --accent:#2f6fed;--accent-soft:#e8f0fe;--ok:#1a9e5c;--warn:#d97706;
  --err:#d64545;--radius:12px;--shadow:0 1px 3px rgba(16,30,54,.08);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif;
  background:var(--bg);color:var(--text)}
.layout{display:flex;min-height:100vh;min-height:100dvh}

/* ---------- 侧栏 ---------- */
.sidebar{width:220px;flex:none;padding:20px 14px;background:var(--card);
  border-right:1px solid var(--line);display:flex;flex-direction:column;gap:16px;
  position:sticky;top:0;height:100vh;height:100dvh}
.brand{display:flex;align-items:center;gap:10px;padding:0 8px}
.brand-mark{width:38px;height:38px;border-radius:10px;flex:none;display:flex;
  align-items:center;justify-content:center;font-size:20px;background:var(--accent-soft)}
.brand-name{font-weight:700}
.brand-sub{font-size:12px;color:var(--muted)}
.nav{display:flex;flex-direction:column;gap:4px}
.nav-item{position:relative;text-align:left;padding:10px 12px;border:0;border-radius:8px;
  background:transparent;color:var(--text);font-size:15px;cursor:pointer}
.nav-item:hover{background:var(--accent-soft)}
.nav-item.active{background:var(--accent);color:#fff}
.sidebar-foot{margin-top:auto;font-size:12px;color:var(--muted);padding:0 8px}

/* ---------- 主区 ---------- */
.main{flex:1;min-width:0;width:100%;padding:24px 28px 96px;max-width:900px}
.page{display:none}.page.active{display:block}
h2.page-title{margin:4px 0 4px;font-size:20px}
.page-desc{color:var(--muted);font-size:13px;margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;margin-bottom:14px;box-shadow:var(--shadow)}
.card-title{font-weight:600;margin-bottom:4px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.card-sub{color:var(--muted);font-size:13px;margin:0 0 12px}
.hint{color:var(--muted);font-size:13px;margin:6px 0}
.muted{color:var(--muted)}.sm{font-size:12px}
.stack{display:flex;flex-direction:column;gap:8px}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.mt{margin-top:10px}

/* ---------- 控件 ---------- */
input[type=text],input[type=number],input[type=password],textarea,select{
  background:#fff;border:1px solid var(--line);border-radius:8px;color:var(--text);
  padding:8px 10px;width:100%;font:inherit}
input[type=number]{width:auto}
textarea{resize:vertical;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent)}
label.field{display:block;margin:10px 0}
label.field>span{display:block;color:var(--muted);font-size:12px;margin-bottom:4px}
.switch-row{display:flex;align-items:flex-start;gap:10px;padding:10px 0;cursor:pointer}
.switch-row input{width:17px;height:17px;margin-top:2px;accent-color:var(--accent);flex:none}
.switch-row .sub{display:block;font-size:13px;color:var(--muted)}
.btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);
  background:#fff;color:var(--text);border-radius:8px;padding:8px 14px;cursor:pointer;font-size:14px}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{opacity:.92;color:#fff}
.btn.small{padding:5px 12px;font-size:13px;min-height:0}
.btn:disabled{opacity:.5;cursor:default}
.btn.danger{color:var(--err)}.btn.danger:hover{background:var(--err);color:#fff;border-color:var(--err)}
.btn-row{display:flex;gap:10px;align-items:center;margin:10px 0;flex-wrap:wrap}

/* ---------- 徽标/状态点 ---------- */
.badge{font-size:11px;padding:1px 8px;border-radius:99px;background:var(--accent-soft);color:var(--accent);font-weight:500}
.dot{display:inline-flex;align-items:center;gap:6px;font-size:13px}
.dot::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--muted)}
.dot.ok::before{background:var(--ok)}.dot.bad::before{background:var(--err)}.dot.wait::before{background:var(--warn)}
.pill{font-size:11px;padding:2px 9px;border-radius:99px;white-space:nowrap;border:1px solid transparent}
.pill.on{color:var(--ok);background:#e7f6ee;border-color:#bfe6d0}
.pill.off{color:var(--muted);background:#eef1f5;border-color:var(--line)}
.pill.warn{color:#b45309;background:#fef3e2;border-color:#f3d9b0}
.chip{display:inline-flex;align-items:center;gap:5px;background:#eef1f5;border:1px solid var(--line);
  color:var(--text);border-radius:99px;padding:2px 6px 2px 11px;font-size:12px;margin:2px}
.chip b{cursor:pointer;font-weight:700;color:var(--muted);padding:0 3px;border-radius:99px}
.chip b:hover{color:var(--err)}
.tag{display:inline-block;font-size:10px;color:var(--accent);background:var(--accent-soft);
  border-radius:5px;padding:0 5px;margin-left:6px}
.tag.amber{color:#b45309;background:#fef3e2}
.tag.warn{color:#b45309;background:#fef3e2}
/* ---------- 表格 ---------- */
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
th{color:var(--muted);font-weight:500;font-size:12px}
tr:last-child td{border-bottom:0}
.meta{color:var(--muted);font-size:12px;word-break:break-all}
.del{color:var(--err);background:transparent;border:0;cursor:pointer;font-size:13px;padding:4px 6px}
.st{font-size:12px;white-space:nowrap}.st.ok{color:var(--ok)}.st.bad{color:var(--err)}.st.wait{color:var(--muted)}

/* ---------- 概览统计 ---------- */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.stat{background:#fafbfc;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.stat .n{font-size:22px;font-weight:700}
.stat .l{font-size:12px;color:var(--muted)}
.lib-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.lib{display:flex;align-items:center;gap:10px;background:#fafbfc;border:1px solid var(--line);
  border-radius:10px;padding:10px 12px}
.lib .ic{font-size:20px}
.lib .t{font-weight:600;font-size:14px}
.lib .c{font-size:12px;color:var(--muted)}
.lib .pin{display:inline-flex;align-items:center;gap:4px;font-size:12px;color:var(--muted);
  cursor:pointer;white-space:nowrap;padding:2px 8px;border-radius:99px;border:1px solid var(--line);background:#fff}
.lib .pin input{margin:0;accent-color:var(--accent)}
.lib:has(.pin input:checked){border-color:var(--accent);background:var(--accent-soft)}
.group-title{font-size:13px;font-weight:600;margin:16px 0 8px;display:flex;align-items:center;gap:8px}
.group-title:first-of-type{margin-top:0}
.divider{border-top:1px solid var(--line);margin:16px 0}

/* ---------- 弹窗/日志/toast ---------- */
.prio-input{width:74px}
pre.log{max-height:240px;overflow:auto;background:#0f1115;color:#d6dae0;border-radius:8px;
  padding:10px;font-size:11px;line-height:1.5;margin:6px 0 0;white-space:pre-wrap}
#toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%) translateY(8px);
  background:#222;color:#fff;padding:9px 18px;border-radius:99px;font-size:13px;opacity:0;
  transition:.22s;pointer-events:none;z-index:80;max-width:90vw}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
#toast.ok{background:var(--ok)}#toast.fail{background:var(--err)}

/* ---------- 移动端 ---------- */
.bottom-nav{display:none}
@media(max-width:760px){
  .sidebar{display:none}
  .main{padding:max(16px,env(safe-area-inset-top,0px)) 14px
    calc(64px + env(safe-area-inset-bottom,8px));max-width:100%}
  h2.page-title{font-size:18px}
  input[type=text],input[type=password],textarea,select{font-size:16px}
  .btn{min-height:42px}
  .bottom-nav{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:45;
    height:calc(58px + env(safe-area-inset-bottom,0px));box-sizing:border-box;align-items:center;
    background:rgba(255,255,255,.97);border-top:1px solid var(--line);backdrop-filter:blur(6px);
    padding-bottom:env(safe-area-inset-bottom,0px)}
  .bottom-nav .nav-item{flex:1;display:flex;align-items:center;justify-content:center;
    height:58px;text-align:center;padding:0 2px;font-size:12px;border-radius:0;white-space:nowrap}
  .bottom-nav .nav-item.active{background:transparent;color:var(--accent);font-weight:700}
}
/* 加固影视浏览：海报墙 + 播放器 */
.gb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px;margin-top:6px}
.gb-card{cursor:pointer;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card);
  transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column}
.gb-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.12)}
.gb-poster{position:relative;width:100%;aspect-ratio:2/3;background:#0f1115 center/cover no-repeat;display:block}
.gb-rem{position:absolute;right:4px;top:4px;background:rgba(0,0,0,.65);color:#fff;font-size:10px;
  padding:1px 6px;border-radius:99px;max-width:90%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gb-cap{padding:5px 6px;font-size:12px;line-height:1.3}
.gb-t{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:30px}
.gb-src{color:var(--muted);font-size:10px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gb-mask{position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:9999;display:flex;align-items:center;
  justify-content:center;padding:14px}
.gb-player{width:min(960px,100%);background:#111;border-radius:12px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.gb-player-bar{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#1c1f26;color:#eee;font-size:13px}
</style>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.13/dist/hls.min.js" async></script>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">🎬</div>
      <div><div class="brand-name">trim-media-online</div><div class="brand-sub">管理台 · v__TMO_VERSION__</div></div>
    </div>
    <nav class="nav" id="nav">
      <button class="nav-item active" data-page="overview">概览</button>
      <button class="nav-item" data-page="sources">资源站</button>
      <button class="nav-item" data-page="danmu">弹幕</button>
      <button class="nav-item" data-page="search">搜索</button>
      <button class="nav-item" data-page="about">关于</button>
    </nav>
    <div class="sidebar-foot">
      <span id="globalState" class="dot wait">检测中…</span>
      <div class="muted" style="margin-top:6px;line-height:1.5">
        v<span id="globalVer">__TMO_VERSION__</span> · <span id="globalMode">检测中</span>
      </div>
    </div>
  </aside>

  <main class="main">

    <!-- ============ 概览 ============ -->
    <section class="page active" id="page-overview">
      <h2 class="page-title">概览 <span class="badge" id="ovVer" style="font-size:11px;vertical-align:middle">v__TMO_VERSION__</span></h2>
      <p class="page-desc">在飞牛原生搜索与媒体库中注入在线影视，点击直接调用飞牛原生播放器。</p>

      <div class="card">
        <div class="card-title">运行统计</div>
        <div class="stat-grid">
          <div class="stat"><div class="n" id="ovSrcN">-</div><div class="l">启用资源站</div></div>
          <div class="stat"><div class="n" id="ovCacheN">-</div><div class="l">已缓存在线条目</div></div>
          <div class="stat"><div class="n" id="ovHotN">-</div><div class="l">热门榜单条目</div></div>
          <div class="stat"><div class="n" id="ovCatN">-</div><div class="l">单源独立库</div></div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">虚拟媒体库</div>
        <p class="card-sub">榜单四库可开关，单源独立库随源配置生成；每张库卡可单独「置顶」。</p>

        <div class="group-title">① 热门资源 <span class="muted sm" style="font-weight:400">豆瓣真实榜单，点进片子才搜源播放，优先高质量源</span></div>
        <div class="lib-grid" id="hotLibs"></div>
        <label class="switch-row">
          <input type="checkbox" id="hotEnabled"/>
          <span>在飞牛影视媒体库显示热门四库
            <span class="sub">🎬热门电影 · 📺热门剧集 · 🌸动漫新番 · 🎤热门综艺（独立开关，不影响单源独立库）</span></span>
        </label>
        <label class="field" style="max-width:240px">
          <span>榜单自动刷新间隔（小时，1–24）</span>
          <input type="number" id="hotInterval" min="1" max="24"/>
        </label>
        <div class="hint" id="hotStatus">等待加载状态…</div>
        <div class="btn-row">
          <button class="primary small" onclick="saveHotCfg()">保存热门设置</button>
          <button class="small" onclick="refreshHot()">立即刷新榜单</button>
        </div>

        <div class="divider"></div>
        <div class="group-title">② 单源独立媒体库</div>
        <p class="card-sub">在「资源站」页给某个源勾选「独立库」，该源会单独生成一张按分类深翻的媒体库卡片，与榜单四库互不影响。</p>
        <div class="lib-grid" id="catLibs"><div class="muted sm">暂无独立库</div></div>
        <div class="hint">独立库在分类路由建立后自动出现（约 1-2 分钟）；分类路由每 6 小时重建一次。</div>
      </div>
    </section>

    <!-- ============ 资源站（一键拉取 / 代理 / 资源列表） ============ -->
    <section class="page" id="page-sources">
      <h2 class="page-title">资源站与订阅</h2>
      <p class="page-desc">从订阅一键拉取源、按需配置代理，资源列表统一启停、测速、看健康画像与调权。</p>

      <div class="card">
        <div class="card-title">一键拉取 · LunaTV 定时同步 <span class="badge" id="lunaBadge">未同步</span>
          <button class="small" style="margin-left:auto" onclick="loadLunaStatus()">刷新状态</button></div>
        <p class="card-sub">从 <code>hafrey1/LunaTV-config</code> 定时拉取源清单：自动去重、逐个测速、可用源自动入库到下方资源列表；
          连续两轮失败的源自动禁用（可在列表恢复）。也可填任意 LunaTV / MoonTV 配置地址（JSON / Base58 / Base64）。</p>
        <div class="row" style="display:grid;grid-template-columns:190px 1fr;gap:10px;align-items:center">
          <select id="lunaPreset" onchange="saveLunaCfg()">
            <option value="jin18">精简版（推荐）</option>
            <option value="jingjian">精简+</option>
            <option value="full">完整版</option>
          </select>
          <input type="text" id="lunaUrl" placeholder="可选：自定义配置 URL，留空使用上方预设" onchange="saveLunaCfg()"/>
        </div>
        <div class="row" style="display:grid;grid-template-columns:130px 150px 1fr auto;gap:10px;align-items:center;margin-top:10px">
          <label class="switch-row" style="margin:0">
            <input type="checkbox" id="lunaSyncEnable" onchange="saveLunaCfg()"/><span>定时同步</span></label>
          <label style="display:flex;align-items:center;gap:6px;font-size:13px">每
            <input type="number" id="lunaInterval" min="1" max="168" style="width:64px" onchange="saveLunaCfg()"/> 小时</label>
          <label class="switch-row" style="margin:0">
            <input type="checkbox" id="lunaAutoDisable" onchange="saveLunaCfg()"/><span>死源自动禁用</span></label>
          <button class="primary small" style="justify-content:center" onclick="lunaSyncNow(this)">立即同步</button>
        </div>
        <div class="hint" id="lunaMsg">尚未同步。点「立即同步」拉取配置并测速。</div>
        <div id="lunaReport" class="muted sm" style="margin-top:8px"></div>
      </div>

      <div class="card">
        <div class="card-title">代理（可选）
          <label style="float:right;display:flex;align-items:center;gap:6px;font-size:12px;font-weight:400;cursor:pointer">
            <input type="checkbox" id="subProxyEnable" style="width:14px;height:14px;accent-color:var(--accent)" onchange="onSubProxyToggle()"/> 启用代理</label></div>
        <p class="card-sub">用于<strong>拉取 LunaTV 配置</strong>与<strong>源 API 请求</strong>（测速/搜索/分类）；<strong>媒体播放仍直连</strong>。支持两种格式：
          <code>https://ac9.cc.cd/</code>（CORSAPI 式 URL 前缀中转，自动请求 <code>?url=原地址</code>）或
          <code>http://用户:密码@主机:端口</code>（Clash 等 HTTP 代理）。清空=直连。</p>
        <div class="row" style="display:grid;grid-template-columns:150px 1fr auto auto;gap:10px">
          <select id="subProxyMode" onchange="onSubProxyModeChange()" disabled>
            <option value="auto">自动识别</option>
            <option value="relay">URL 前缀中转</option>
            <option value="http">HTTP 代理</option>
          </select>
          <input type="text" id="subProxyUrl" placeholder="https://ac9.cc.cd/" disabled/>
          <button class="small" id="subProxySaveBtn" onclick="saveSubProxy(true)" disabled>保存并测试</button>
          <button class="small" id="subProxyClearBtn" onclick="clearSubProxy()" disabled>清空(直连)</button>
        </div>
        <div class="hint" id="subProxyHint">中转示例：<code>https://ac9.cc.cd/</code>；HTTP 代理示例：<code>http://Clash:密码@192.168.x.x:7890</code></div>
        <div id="subProxyMsg" class="muted sm" style="margin-top:6px"></div>
      </div>

      <div class="card">
        <div class="card-title">资源列表 <span class="badge" id="srcCount"></span>
          <label style="display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:400;cursor:pointer">
            <input type="checkbox" id="preferQ" style="width:14px;height:14px;accent-color:var(--accent)" onchange="savePreferQ()"/>热门优先高质量源</label>
          <button class="small" style="margin-left:auto" onclick="testAll()">全部测速</button>
          <button class="small" onclick="savePriority()">保存权重</button>
          <button class="small" onclick="resetPriority()">默认权重</button>
          <button class="small" onclick="restoreBuiltin()">清空全部源</button>
        </div>
        <p class="card-sub">成功率 / 延迟 / 状态来自真实播放探测的源健康画像（死源自动降权 15 分钟）；权重影响热门搜源排序，-100–100，留空用默认。修改权重后点「保存权重」。</p>
        <div style="overflow-x:auto">
        <table>
          <thead><tr><th style="width:42px">启用</th><th style="width:96px">选项</th><th>资源站</th>
            <th style="width:150px">连通性</th><th style="width:60px">测试</th>
            <th style="width:62px">成功率</th><th style="width:62px">延迟</th>
            <th style="width:74px">状态</th><th style="width:90px">权重</th><th style="width:36px"></th></tr></thead>
          <tbody id="srcRows"><tr><td colspan="10" class="muted">加载中…</td></tr></tbody>
        </table>
        </div>
        <div class="row mt" style="display:grid;grid-template-columns:150px 1fr 90px auto;gap:10px" id="addGrid">
          <input type="text" id="addName" placeholder="名称（可选）"/>
          <input type="text" id="addApi" placeholder="苹果CMS JSON 接口，如 https://xxx.com/api.php/provide/vod/at/json"/>
          <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer">
            <input type="checkbox" id="addStandalone" style="width:15px;height:15px;accent-color:var(--accent)"/>独立库</label>
          <button class="primary small" style="justify-content:center" onclick="addSource()">添加</button>
        </div>
        <div class="hint">「独立库」= 该站单独生成一张媒体库卡片；「非过滤」= 不按标题/备注过滤解说/预告/花絮。
          本项目不内置任何源：请在上方粘贴你自行获取的苹果 CMS V10 JSON 接口，或用本页顶部「一键拉取」从 LunaTV 配置定时拉取。请仅接入你有权访问的接口。</div>
      </div>
    </section>



    <!-- ============ 弹幕 ============ -->
    <section class="page" id="page-danmu">
      <h2 class="page-title">弹幕</h2>
      <p class="page-desc">把 <a href="https://github.com/huangxd-/danmu_api" target="_blank" rel="noopener">danmu_api</a> 提供的弹幕转成 ASS 字幕轨，走飞牛播放器自带的外挂字幕渲染。本项目不内置、不代理任何弹幕服务。</p>

      <div class="card">
        <div class="card-title">弹幕接口</div>
        <label class="switch-row"><input type="checkbox" id="danmuEnabled"/>
          <span>启用弹幕<span class="sub">关闭后不再生成弹幕字幕轨，播放完全不受影响</span></span></label>
        <label class="switch-row"><input type="checkbox" id="danmuAuto"/>
          <span>自动加载弹幕<span class="sub">进入播放页默认选中「弹幕」字幕；关闭后可在字幕菜单手动选择</span></span></label>
        <label class="field"><span>接口地址</span>
          <input type="text" id="danmuApi" placeholder="https://danmu.xxx.workers.dev 或 http://192.168.1.10:9321"/></label>
        <label class="field" style="max-width:360px"><span>接口 Token<span class="muted" style="font-weight:400">（默认 87654321 可留空）</span></span>
          <input type="text" id="danmuToken" placeholder="87654321"/></label>
        <div class="row">
          <label class="field" style="max-width:180px"><span>时间偏移（秒）</span>
            <input type="number" id="danmuOffset" min="-60" max="60" step="0.5" style="width:100%"/></label>
          <label class="field" style="max-width:180px"><span>最多弹幕条数</span>
            <input type="number" id="danmuLimit" min="100" max="3000" step="100" style="width:100%"/></label>
        </div>
        <div class="btn-row">
          <button class="primary small" onclick="saveDanmu()">保存弹幕设置</button>
          <button class="small" onclick="testDanmu()">测试连接</button>
        </div>
        <div id="danmuMsg" class="muted sm" style="margin-top:6px"></div>
      </div>

      <div class="card">
        <div class="card-title">播放去广告</div>
        <label class="switch-row"><input type="checkbox" id="adFilterEnabled"/>
          <span>剥除片头/片中广告分片<span class="sub">默认关闭。开启后播放当前线路时分析 m3u8，移除明显的广告分片；判断不确定就保留原片，不影响播放</span></span></label>
        <div class="btn-row">
          <button class="primary small" onclick="saveAdFilter()">保存</button>
        </div>
        <div id="adFilterMsg" class="muted sm" style="margin-top:6px"></div>
      </div>

      <div class="card">
        <div class="card-title">使用说明</div>
        <div class="stack sm muted" style="line-height:1.7">
          <div>· 先自行部署 danmu_api，例如：<code>docker run -d -p 9321:9321 -e TOKEN=87654321 --name danmu-api logvar/danmu-api:latest</code></div>
          <div>· 也可用 Cloudflare Workers / Vercel 等云端部署：地址填 <code>https://xxx.workers.dev</code>，自定义 Token 会按 <code>/Token/api/v2/...</code> 自动拼接，不用手写路径。</div>
          <div>· 本地或内网填 <code>http://NAS地址:9321</code>；漏写 <code>https://</code> 时公网域名会自动按 https 访问。</div>
          <div>· CF 免费版单次请求有子请求上限，长视频可能只拿到前半段弹幕；官方也说明 CF 对 B 站有风控，追求稳定建议本地 Docker 或 Vercel/Netlify。</div>
          <div>· danmu_api 默认限流 3 次/分钟，匹配失败频繁时可在其环境变量调大 <code>RATE_LIMIT_MAX_REQUESTS</code>。</div>
          <div>· 播放时字幕菜单会出现「弹幕」；无匹配或接口超时只会显示空字幕，不影响正片播放。</div>
          <div>· 按片名 + SxxEyy 自动匹配，冷门片或命名不规范的片源可能匹配不到；可用时间偏移校准。</div>
          <div>· 弹幕依赖播放器的 ASS 外挂字幕能力（Web 端内置 libass）；TV 端与手机端以实际表现为准。</div>
        </div>
      </div>
    </section>

    <!-- ============ 搜索 ============ -->
    <section class="page" id="page-search">
      <h2 class="page-title">搜索设置</h2>
      <div class="card">
        <label class="switch-row"><input type="checkbox" id="onlineFirst"/>
          <span>在线资源结果前排展示<span class="sub">在线片库更齐全；关闭则本地优先</span></span></label>
        <label class="field" style="max-width:240px"><span>每个关键词最多注入条数</span>
          <input type="number" id="maxn" min="1" max="50" style="width:100%"/></label>
        <label class="switch-row"><input type="checkbox" id="junk"/>
          <span>按关键词过滤噪音<span class="sub">标题或备注命中噪音词则不注入</span></span></label>
        <label class="field"><span>噪音关键词 <span id="kwN" class="muted"></span>
          <span style="float:right">
            <button class="small" type="button" onclick="resetKw()">恢复默认</button>
            <button class="small" type="button" onclick="toggleKwEdit()">批量编辑</button>
          </span></span>
          <div id="kwChips" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px"></div>
          <div id="kwEdit" style="display:none;margin-bottom:8px">
            <textarea id="kwArea" rows="4" placeholder="每行一个，或逗号/顿号分隔，如：解说,预告片,花絮,枪版"></textarea>
            <button class="small" type="button" onclick="applyKwText()" style="margin-top:6px">应用文本</button>
          </div>
          <div class="row"><input type="text" id="kwAdd" placeholder="添加关键词后回车" style="flex:1"/>
            <button class="small" type="button" onclick="addKw()">添加</button></div>
        </label>
        <div class="btn-row"><button class="primary small" onclick="saveCfg()">保存设置</button></div>
      </div>

      <div class="card">
        <div class="card-title">播放线路</div>
        <label class="switch-row"><input type="checkbox" id="lineFastest"/>
          <span>自动选最快线路<span class="sub">起播时并行测速、自动选首字节最快的线路；同一集短时间内固定用它</span></span></label>
        <label class="field" style="max-width:260px"><span>参与测速的线路数</span>
          <input type="number" id="fastestMax" min="2" max="12" style="width:100%"/></label>
        <label class="field" style="max-width:260px"><span>测速超时（秒）</span>
          <input type="number" id="fastestTimeout" min="1" max="10" step="0.5" style="width:100%"/></label>
        <label class="switch-row"><input type="checkbox" id="lineAutofail"/>
          <span>坏线自动切换<span class="sub">当前线路失效/文件不存在时自动换到可用线路，并短时跳过坏线（关闭则纯手动切线）</span></span></label>
        <div class="btn-row"><button class="primary small" onclick="saveLines()">保存播放设置</button></div>
      </div>

      <div class="card">
        <div class="card-title">已缓存在线条目 <span class="badge" id="cacheN"></span></div>
        <div class="row"><input type="text" id="kw" placeholder="按标题过滤（在飞牛搜索过的会出现在这里）" style="flex:1"/>
          <button class="small" onclick="loadOnline()">刷新</button></div>
        <table style="margin-top:10px">
          <thead><tr><th>标题</th><th style="width:100px">来源</th><th style="width:70px">集数</th></tr></thead>
          <tbody id="rows"><tr><td colspan="3" class="muted">加载中…</td></tr></tbody>
        </table>
      </div>
    </section>

    <!-- ============ 关于 ============ -->
    <section class="page" id="page-about">
      <h2 class="page-title">关于</h2>
      <div class="card">
        <div class="card-title">🎬 trim-media-online · 飞牛影视在线能力扩展</div>
        <p class="card-sub">在原生搜索 / 媒体库注入在线影视并直接调用飞牛原生播放器播放。</p>
        <div class="hint" id="aboutEdition"></div>
      </div>

      <div class="card">
        <div class="card-title">⚖️ 免责声明与版权声明</div>
        <div class="stack sm muted" style="line-height:1.7">
          <div><b>1. 工具性质：</b>本扩展是<b>开源、免费</b>的技术研究与个人媒体库整理工具，仅在你自己的 NAS / 设备上本地运行。它是一个中立的“播放器 / 接口聚合”技术框架，本身<b>不提供、不存储、不上传、不分发、不转码</b>任何影视、图片、字幕、播放地址或资源站点信息，也<b>不内置任何资源数据库、订阅、站点地址、爬虫或执行 jar</b>。</div>
          <div><b>2. 不内置源、由你自备：</b>所有在线内容均来自你<b>自行添加</b>的第三方接口、TVBox 订阅，或你本人上传的脚本 / 执行 jar；是否添加、添加什么、是否启用，完全由你决定并自行承担。请仅使用你拥有合法授权或有权访问的内容与组件。</div>
          <div><b>3. 版权归原权利人：</b>第三方接口返回内容的版权归原权利人所有。本项目不依附、不代表任何内容提供方，不对任何第三方内容的合法性、准确性、可用性负责；如涉及版权问题，请联系内容实际提供方处理。</div>
          <div><b>4. 仅供学习交流：</b>本工具仅供学习、研究与个人合法播放自有或已获授权内容使用，<b>不得用于商业用途，不得下载、录制、再传播任何侵权内容</b>。请遵守你所在地的法律法规。</div>
          <div><b>5. 风险与责任：</b>第三方接口可能失效、变更或包含不当内容；使用过程中产生的流量、账号、费用与一切法律责任均由<b>使用者本人</b>承担，与本工具作者无关。请合法、自律使用，并妥善管理设备与访问权限，避免 18 周岁以下人员接触不适宜内容。</div>
          <div><b>6. 侵权处理：</b>如任何权利人认为本工具的某项技术实现涉及其合法权益，可通过项目仓库 Issue 联系作者，核实后将及时处理。</div>
        </div>
      </div>
    </section>
  </main>
</div>

<nav class="bottom-nav" id="bottomNav">
  <button class="nav-item active" data-page="overview">概览</button>
  <button class="nav-item" data-page="sources">资源站</button>
  <button class="nav-item" data-page="danmu">弹幕</button>
  <button class="nav-item" data-page="search">搜索</button>
  <button class="nav-item" data-page="about">关于</button>
</nav>

<div id="toast"></div>

<script>
const $=(id)=>document.getElementById(id);
const $$=(sel)=>Array.from(document.querySelectorAll(sel));
let CFG=null,KWS=[],STATUS=null,PRIO={};
const FEAT_DDUO=false,FEAT_ADULT=false;

const APP_PREFIX="/app/trim-media-online";
const API_BASE=location.pathname.startsWith(APP_PREFIX)?APP_PREFIX:"";
const apiUrl=(p)=>API_BASE+p;

function toast(m,kind){const t=$("toast");t.textContent=m;t.className="show "+(kind==="fail"?"fail":"ok");
  clearTimeout(window._tt);window._tt=setTimeout(()=>t.className="",2200);}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
async function jget(p){const r=await fetch(apiUrl(p));if(!r.ok)throw new Error(p+" "+r.status);return r.json();}
async function jpost(p,b){const r=await fetch(apiUrl(p),{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify(b||{})});return r.json();}

/* ---------- 页面切换 ---------- */
async function switchPage(page){
  $$(".page").forEach(el=>el.classList.toggle("active",el.id==="page-"+page));
  $$("[data-page]").forEach(el=>el.classList.toggle("active",el.dataset.page===page));
  window.scrollTo(0,0);
  if(page==="overview"){try{renderOverview();}catch(e){console.error(e);}loadLibs().then(renderLibrary).catch(e=>console.error(e));}
  if(page==="sources"){
    try{renderSources();}catch(e){}
    try{loadLunaStatus();}catch(e){}
    try{if(typeof initSubProxy==="function")initSubProxy();}catch(e){}
  }
  if(page==="danmu"){try{if(!CFG)await loadStatus();}catch(e){}initDanmu();initAdFilter();}
  if(page==="about"){}
}
$$("[data-page]").forEach(b=>b.addEventListener("click",()=>switchPage(b.dataset.page)));

/* ---------- 概览 ---------- */
function renderOverview(){
  if(!STATUS||!CFG)return;
  const c=STATUS.charts&&STATUS.charts.counts||{};
  $("ovSrcN").textContent=CFG.sources.filter(s=>s.enabled).length;
  $("ovCacheN").textContent=STATUS.cached_titles||0;
  $("ovHotN").textContent=(c.movie||0)+(c.tv||0)+(c.anime||0)+(c.variety||0);
  $("ovCatN").textContent=(CFG.sources||[]).filter(x=>x.standalone).length;
}

/* ---------- 虚拟媒体库 ---------- */
let LIBS=[];
async function loadLibs(){
  try{const r=await jget("/v/api/ext/libs");LIBS=(r.data&&r.data.libs)||[];
  }catch(e){LIBS=[];}
}
function catKeyOf(title){
  if(/电影/.test(title))return "movie"; if(/剧/.test(title))return "tv";
  if(/动漫|番/.test(title))return "anime"; if(/综艺/.test(title))return "variety"; return "";
}
function libCardHtml(L,ic){
  return `<div class="lib" data-g="${L.guid}"><div class="ic">${ic}</div>
    <div style="flex:1;min-width:0"><div class="t">${esc(L.title)}</div>
      <div class="c">${L.group==="hot"?(L.count+" 条"):(L.count?("路由 "+L.count):"建库中…")}</div></div>
    <label class="pin" title="在飞牛影视媒体库列表中置顶">
      <input type="checkbox" ${L.pinned?"checked":""} onchange="togglePin('${L.guid}',this)"/>置顶</label>
  </div>`;
}
async function togglePin(guid,el){
  try{
    const r=await jpost("/v/api/ext/lib/pin", {guid,pinned:el.checked});
    if(r.code===0){toast(el.checked?"已置顶":"已取消置顶");LIBS.forEach(x=>{if(x.guid===guid)x.pinned=el.checked;});}
    else{el.checked=!el.checked;toast(r.msg||"设置失败","fail");}
  }catch(e){el.checked=!el.checked;toast("设置失败","fail");}
}
function renderLibrary(){
  if(!STATUS)return;
  $("hotEnabled").checked=CFG.hot_library_enabled!==false;
  $("hotInterval").value=Math.round((CFG.hot_refresh_interval||21600)/3600);
  const c=STATUS.charts&&STATUS.charts.counts||{};
  const hotIc={movie:"🎬",tv:"📺",anime:"🌸",variety:"🎤"};
  if(LIBS.length){
    $("hotLibs").innerHTML=LIBS.filter(x=>x.group==="hot").map(L=>libCardHtml(L,hotIc[catKeyOf(L.title)]||"🔥")).join("");
  }else{
    $("hotLibs").innerHTML=[["movie","🎬","热门电影",c.movie||0],["tv","📺","热门剧集",c.tv||0],["anime","🌸","动漫新番",c.anime||0],["variety","🎤","热门综艺",c.variety||0]]
        .map(([k,ic,t,n])=>`<div class="lib"><div class="ic">${ic}</div><div><div class="t">${t}</div><div class="c">${n} 条</div></div></div>`).join("");
  }
  const stand=((CFG&&CFG.sources)||[]).filter(x=>x.standalone);
  const sc=(STATUS.catalog&&STATUS.catalog.standalone)||{};
  if(stand.length){
    $("catLibs").innerHTML=stand.map(x=>{
      const cats2=sc[x.id]||{};
      const n=Object.values(cats2).filter(v=>v>0).length;
      return `<div class="lib"><div class="ic">📡</div><div><div class="t">${esc(x.name)}</div>
        <div class="c">${n?("类目 "+n+"/4"):"建库中…"}</div></div></div>`;
    }).join("");
  }else{
    $("catLibs").innerHTML='<div class="muted sm">暂无独立库（在资源站页勾选「独立库」）</div>';
  }
  $("hotStatus").textContent=(STATUS.charts&&STATUS.charts.refreshing?"正在后台刷新榜单…":"最近刷新："+fmtTs(STATUS.charts&&STATUS.charts.updated_at))
    +` · 数据源 ${(STATUS.charts&&STATUS.charts.provider_ok)||0}/${(STATUS.charts&&STATUS.charts.provider_total)||0}`
    +(STATUS.charts&&STATUS.charts.last_error?(" · "+STATUS.charts.last_error):"");
}
function fmtTs(ts){if(!ts)return"尚未刷新";const d=new Date(ts*1000),p=n=>String(n).padStart(2,"0");
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;}
async function saveHotCfg(){
  const body={hot_library_enabled:$("hotEnabled").checked,
    hot_refresh_interval:Math.max(1,Math.min(24,parseInt($("hotInterval").value)||6))*3600};
  const r=await jpost("/v/api/ext/config", body);
  if(r.code===0){Object.assign(CFG,body);toast("热门设置已保存");await loadLibs();renderLibrary();}else toast(r.msg||"保存失败","fail");
}
async function refreshHot(){
  toast("开始刷新榜单…");
  const r=await jpost("/v/api/ext/hot/refresh", {});
  await loadStatus();await loadLibs();renderLibrary();
  toast(r.code===0?"榜单已刷新":(r.msg||"刷新失败"),r.code===0?"ok":"fail");
}

/* ---------- 资源站 ---------- */
function renderSources(){
  const srcs=CFG.sources;
  $("srcCount").textContent=srcs.filter(x=>x.enabled).length+"/"+srcs.length+" 启用";
  $("preferQ").checked=CFG.prefer_quality_source!==false;
  if(!srcs.length){
    $("srcRows").innerHTML='<tr><td colspan="10" class="muted">尚未添加任何资源站——请用顶部「一键拉取」或下方粘贴苹果 CMS V10 JSON 接口添加。未配置源时，在线搜索与热门榜单均无内容。</td></tr>';
    return;
  }
  const pr=STATUS.source_priority||{}, ov=CFG.source_priority||{};
  $("srcRows").innerHTML=srcs.map(src=>{
    const eff=pr[src.id]||0, custom=ov[src.id];
    return `<tr data-id="${src.id}">
      <td><input type="checkbox" class="en" ${src.enabled?"checked":""} style="accent-color:var(--accent);width:16px;height:16px"/></td>
      <td style="white-space:nowrap">
        <label title="把该资源站单独生成一张媒体库卡片" style="display:inline-flex;align-items:center;gap:2px;font-size:11px;cursor:pointer">
          <input type="checkbox" class="sa" ${src.standalone?"checked":""}
           ${(src.enabled&&!(FEAT_DDUO&&src.xsrc))?"":"disabled"} style="width:15px;height:15px;accent-color:var(--accent)"/>库</label>
        <label title="非过滤：独立库内不按标题/备注过滤解说/预告/花絮" style="display:inline-flex;align-items:center;gap:2px;font-size:11px;cursor:pointer;margin-left:4px">
          <input type="checkbox" class="lf" ${src.loose_filter?"checked":""}
           ${(src.enabled&&src.standalone&&!(FEAT_DDUO&&src.xsrc))?"":"disabled"} style="width:15px;height:15px;accent-color:var(--warn)"/>非过滤</label>
      </td>
      <td><div style="font-weight:500">${esc(src.name)}${src.builtin?'':'<span class="tag amber">自定义</span>'}${src.standalone?'<span class="tag">媒体库</span>':''}</div>
        <div class="meta">${esc(src.api)}</div></td>
      <td class="st wait" data-st>未测</td>
      <td><button class="small" data-test>测试</button></td>
      <td class="sm muted" data-hr="rate">—</td>
      <td class="sm muted" data-hr="lat">—</td>
      <td class="sm" data-hr="grade">—</td>
      <td><input type="number" class="prio-input" min="-100" max="100" data-prio
        value="${custom!=null?custom:''}" placeholder="${eff}"/></td>
      <td><button class="del" data-del title="删除">✕</button></td>
    </tr>`;
  }).join("");
  $$("#srcRows tr").forEach(tr=>{
    const id=tr.dataset.id;
    tr.querySelector(".en").addEventListener("change",()=>toggleEnable(id,tr.querySelector(".en").checked));
    const sa=tr.querySelector(".sa");sa.addEventListener("change",()=>toggleStandalone(id,sa.checked));
    const lf=tr.querySelector(".lf");if(lf)lf.addEventListener("change",()=>toggleLoose(id,lf.checked));
    tr.querySelector("[data-test]").addEventListener("click",()=>testOne(id,tr));
    tr.querySelector("[data-del]").addEventListener("click",()=>delSource(id,srcName(id)));
  });
  loadHealth();
}
function collectPriority(){const m={};$$("[data-prio]").forEach(inp=>{
  const v=inp.value.trim();if(v!=="")m[inp.closest("tr").dataset.id]=parseInt(v)||0;});return m;}
async function savePriority(){
  const r=await jpost("/v/api/ext/source/priority", {priority:collectPriority()});
  if(r.code===0){toast("权重已保存");await loadStatus();renderSources();}else toast(r.msg||"保存失败","fail");
}
async function resetPriority(){
  const r=await jpost("/v/api/ext/source/priority", {priority:{}});
  if(r.code===0){toast("已恢复默认权重");await loadStatus();renderSources();}else toast("失败","fail");
}
async function savePreferQ(){
  const r=await jpost("/v/api/ext/config", {prefer_quality_source:$("preferQ").checked});
  if(r.code===0){CFG.prefer_quality_source=$("preferQ").checked;toast("已保存");}else toast("失败","fail");
}
function srcName(id){const s=CFG.sources.find(x=>x.id===id);return s?s.name:id;}
async function toggleEnable(id,on){
  const sources=CFG.sources.map(s=>({id:s.id,enabled:s.id===id?on:s.enabled}));
  const r=await jpost("/v/api/ext/config", {sources});
  if(r.code===0){CFG.sources.find(x=>x.id===id).enabled=on;
    $("srcCount").textContent=CFG.sources.filter(x=>x.enabled).length+"/"+CFG.sources.length+" 启用";toast(on?"已启用":"已停用");}
  else toast(r.msg||"保存失败","fail");
}
async function toggleStandalone(id,on){
  const r=await jpost("/v/api/ext/source/standalone", {id,standalone:on});
  if(r.code===0){const s=CFG.sources.find(x=>x.id===id);if(s){s.standalone=on;if(!on){s.loose_filter=false;s.adult=false;}}
    renderSources();toast(on?"已生成独立媒体库（后台建库中）":"已取消独立媒体库");}
  else{toast(r.msg||"操作失败","fail");renderSources();}
}
async function toggleLoose(id,on){
  const r=await jpost("/v/api/ext/source/loose-filter", {id,loose_filter:on});
  if(r.code===0){const s=CFG.sources.find(x=>x.id===id);if(s)s.loose_filter=on;renderSources();toast(on?"已开启非过滤":"已恢复严格过滤");}
  else{toast(r.msg||"操作失败","fail");renderSources();}
}
function setSt(tr,html,cls){const el=tr.querySelector("[data-st]");el.className="st "+cls;el.innerHTML=html;}
async function testOne(id,tr){
  setSt(tr,"测试中…","wait");tr.querySelector("[data-test]").disabled=true;
  try{const r=await jpost("/v/api/ext/source/test", {id});const d=r.data;
    if(d.ok)setSt(tr,`✓ ${d.elapsed_ms}ms · ${d.count}条${d.direct?(' · '+d.direct+'直链'):''}`,"ok");
    else setSt(tr,"✕ "+(d.error||"失败")+(d.elapsed_ms?(" · "+d.elapsed_ms+"ms"):""),"bad");
  }catch(e){setSt(tr,"✕ "+e,"bad");}
  tr.querySelector("[data-test]").disabled=false;
}
async function testAll(){
  toast("正在并发测速…");
  $$("#srcRows [data-st]").forEach(el=>{el.className="st wait";el.textContent="测试中…";});
  const r=await jpost("/v/api/ext/source/test-all", {});
  (r.data||[]).forEach(d=>{const tr=$("srcRows").querySelector(`tr[data-id="${d.id}"]`);if(!tr)return;
    if(d.ok)setSt(tr,`✓ ${d.elapsed_ms}ms · ${d.count}条${d.direct?(' · '+d.direct+'直链'):''}`,"ok");
    else setSt(tr,"✕ "+(d.error||"失败"),"bad");});
  toast("测速完成");
}
async function loadHealth(){
  // 源健康画像按 key=源 id 填进资源列表的成功率/延迟/状态列
  let map={};
  try{
    const r=await (await fetch(apiUrl("/v/api/ext/source-health"))).json();
    ((r.data&&r.data.sources)||[]).forEach(s=>{map[s.key]=s;});
  }catch(e){return;}
  const G=["健康","慢","高失败率","冷却中"],GC=["ok","wait","bad","bad"];
  $$("#srcRows tr[data-id]").forEach(tr=>{
    const s=map[tr.dataset.id];if(!s)return;
    const rate=tr.querySelector('[data-hr="rate"]'),lat=tr.querySelector('[data-hr="lat"]'),
          gr=tr.querySelector('[data-hr="grade"]');
    if(!rate)return;
    rate.textContent=Math.round((s.success_rate||0)*100)+"%";
    lat.textContent=s.samples?((s.avg_latency||0).toFixed(1)+"s"):"—";
    gr.textContent=G[s.grade]||"";
    gr.className="st "+(GC[s.grade]||"");
  });
}
async function addSource(){
  const name=$("addName").value.trim(),api=$("addApi").value.trim(),standalone=$("addStandalone").checked;
  if(!api){toast("请填写接口地址","fail");return;}
  const r=await jpost("/v/api/ext/source/add", {name,api,standalone});
  if(r.code===0){toast("已添加");$("addName").value="";$("addApi").value="";$("addStandalone").checked=false;
    await loadStatus();const tr=$("srcRows").querySelector(`tr[data-id="${r.data.id}"]`);if(tr&&!standalone)testOne(r.data.id,tr);}
  else toast(r.msg||"添加失败","fail");
}
// ---------- LunaTV 定时同步 ----------
function lunaReportText(d){
  let s=`新增 ${d.added||0} 个源（配置共 ${d.total||0}，已存在 ${d.duplicate||0}）`;
  s+=`；测速 ${d.probed||0} 个，正常 ${d.ok||0}，失败 ${d.failed||0}`;
  if(d.avg_ms)s+=`，平均延迟 ${d.avg_ms}ms`;
  if((d.disabled||[]).length)s+=`；自动禁用：${d.disabled.slice(0,6).join("、")}${d.disabled.length>6?" 等":""}`;
  if((d.re_enabled||[]).length)s+=`；恢复：${d.re_enabled.slice(0,6).join("、")}`;
  if(d.auto_skipped)s+="；本轮整体失败过多，已跳过自动禁用";
  return s;
}
async function loadLunaStatus(){
  try{
    const r=await jget("/v/api/ext/lunatv/status");
    const d=r.data||{},s=d.sync||{},last=d.last||{};
    const ps=$("lunaPreset"),pu=$("lunaUrl");
    if(ps)ps.value=s.preset||"jin18";
    if(pu&&document.activeElement!==pu)pu.value=s.url||"";
    if($("lunaSyncEnable"))$("lunaSyncEnable").checked=!!s.enabled;
    if($("lunaInterval"))$("lunaInterval").value=s.interval||12;
    if($("lunaAutoDisable"))$("lunaAutoDisable").checked=s.auto_disable!==false;
    if($("lunaBadge"))$("lunaBadge").textContent=last.at?("上次 "+last.at.slice(5,16)):"未同步";
    if($("lunaMsg"))$("lunaMsg").textContent=last.at?lunaReportText(last):"尚未同步。点「立即同步」拉取配置并测速。";
    if($("lunaReport"))$("lunaReport").textContent=last.at?("触发："+(last.trigger==="schedule"?"定时":"手动")+" · 配置："+(last.url||last.preset||"")+" · 同步中："+(d.syncing?"是":"否")):"";
  }catch(e){}
}
async function saveLunaCfg(){
  const body={
    lunatv_sync_enabled:$("lunaSyncEnable").checked,
    lunatv_sync_preset:$("lunaPreset").value,
    lunatv_sync_url:$("lunaUrl").value.trim(),
    lunatv_sync_interval:Math.max(1,Math.min(168,parseInt($("lunaInterval").value)||12)),
    lunatv_auto_disable:$("lunaAutoDisable").checked,
  };
  const r=await jpost("/v/api/ext/config", body);
  if(r.code===0){Object.assign(CFG,body);toast("同步设置已保存");}
  else toast(r.msg||"保存失败","fail");
}
async function lunaSyncNow(btn){
  const old=btn.textContent;
  btn.disabled=true;btn.textContent="同步中…";
  $("lunaMsg").textContent="正在拉取配置并逐个测速，源较多时可能需要 1-2 分钟…";
  try{
    const r=await jpost("/v/api/ext/lunatv/sync",{
      preset:$("lunaPreset").value,url:$("lunaUrl").value.trim()});
    if(r.code!==0){$("lunaMsg").textContent=r.msg||"同步失败";toast(r.msg||"同步失败","fail");return;}
    const d=r.data||{};
    $("lunaMsg").textContent=lunaReportText(d)+" · "+d.at;
    toast(d.added?`已新增 ${d.added} 个源`:"测速完成，无新增源","ok");
    await loadStatus();renderSources();await loadLunaStatus();
  }catch(e){$("lunaMsg").textContent="同步失败："+e;toast("同步失败："+e,"fail");}
  finally{btn.disabled=false;btn.textContent=old;}
}

// ---------- 订阅 / API 中转代理（配置拉取 + 源 API，不影响播放） ----------
function subProxyPlaceholder(mode){
  return mode==="relay"?"https://ac9.cc.cd/":"http://Clash:密码@192.168.x.x:7890";
}
function onSubProxyModeChange(){
  const mode=$("subProxyMode").value,inp=$("subProxyUrl"),hint=$("subProxyHint");
  if(!inp)return;
  inp.placeholder=subProxyPlaceholder(mode);
  if(hint)hint.innerHTML= mode==="relay"
    ? '中转示例：<code>https://ac9.cc.cd/</code>，请求自动拼成 <code>?url=源地址</code>；可填带 <code>{url}</code> 的模板。'
    : 'HTTP 代理示例：<code>http://Clash:密码@192.168.x.x:7890</code>；自动识别模式下按是否带端口判断。';
}
function initSubProxy(){
  const p=(CFG&&CFG.subscription_proxy)||"";
  const mode=(CFG&&CFG.subscription_proxy_mode)||"auto";
  const en=$("subProxyEnable"),sel=$("subProxyMode"),inp=$("subProxyUrl"),sb=$("subProxySaveBtn"),cb=$("subProxyClearBtn"),msg=$("subProxyMsg");
  if(!en)return;
  if(sel)sel.value=mode;
  inp.value=p;en.checked=!!p;
  inp.disabled=!en.checked;if(sel)sel.disabled=!en.checked;sb.disabled=!en.checked;cb.disabled=!p;
  onSubProxyModeChange();
  msg.textContent=p?("当前已启用"+(mode==="relay"?"（URL 前缀中转）":mode==="http"?"（HTTP 代理）":"（自动识别）")+"，作用于配置拉取与源 API"):"当前直连（未设代理）";
  msg.style.color="";
}
function onSubProxyToggle(){
  const en=$("subProxyEnable"),sel=$("subProxyMode"),inp=$("subProxyUrl"),sb=$("subProxySaveBtn");
  inp.disabled=!en.checked;if(sel)sel.disabled=!en.checked;sb.disabled=!en.checked;
  if(en.checked)inp.focus();
}
async function saveSubProxy(test){
  const inp=$("subProxyUrl"),msg=$("subProxyMsg"),mode=$("subProxyMode").value;
  const proxy=inp.value.trim();
  if(!proxy){toast("请填写代理或中转地址，或点清空直连","fail");return;}
  msg.textContent="保存并测试连通性…";msg.style.color="";
  try{
    const r=await jpost("/v/api/ext/subscription-proxy", {proxy,mode});
    if(r.code!==0){msg.textContent="未保存："+(r.msg||"格式错误");msg.style.color="var(--danger)";return;}
    const d=r.data||{};
    if(test){
      msg.textContent=d.test_ok?("✓ 已保存，"+(d.mode==="relay"?"中转":"代理")+"连通（"+(d.test_msg||"")+"），作用于配置拉取与源 API")
                               :("已保存，但连通测试失败："+(d.test_msg||""));
      msg.style.color=d.test_ok?"var(--ok,#3a9)":"var(--warn,#d59a2b)";
    }else{msg.textContent="已保存";}
    $("subProxyClearBtn").disabled=false;
    toast("已保存");
  }catch(e){msg.textContent="请求失败："+String(e);msg.style.color="var(--danger)";}
}
async function clearSubProxy(){
  if(!confirm("清空订阅 / API 中转代理、改为直连？"))return;
  const mode=$("subProxyMode").value;
  const r=await jpost("/v/api/ext/subscription-proxy", {proxy:"",mode});
  if(r.code===0){$("subProxyUrl").value="";$("subProxyEnable").checked=false;
    $("subProxyUrl").disabled=true;$("subProxyMode").disabled=true;$("subProxySaveBtn").disabled=true;$("subProxyClearBtn").disabled=true;
    $("subProxyMsg").textContent="已清空，当前直连";$("subProxyMsg").style.color="";toast("已切回直连");}
  else toast(r.msg||"失败","fail");
}
// ---------- 已导入普通爬虫源管理 ----------
async function delSource(id,name){
  if(!confirm("确定删除资源站「"+name+"」？"))return;
  const r=await jpost("/v/api/ext/source/delete", {id});
  if(r.code===0){toast("已删除");await loadStatus();}else toast(r.msg||"删除失败","fail");
}
async function restoreBuiltin(){
  if(!confirm("确定清空全部资源站？清空后需重新添加源地址。"))return;
  const r=await jpost("/v/api/ext/source/restore", {});
  if(r.code===0){toast("已清空全部源");await loadStatus();}else toast("失败","fail");
}

/* ---------- 搜索设置 / 噪音词 / 缓存 ---------- */
function renderKw(){
  $("kwN").textContent="（共 "+KWS.length+" 个）";
  $("kwChips").innerHTML=KWS.map((k,i)=>`<span class="chip">${esc(k)}<b data-i="${i}" title="删除">×</b></span>`).join("");
  $("kwChips").querySelectorAll("b").forEach(b=>b.onclick=()=>{KWS.splice(+b.dataset.i,1);saveKw();});
}
async function saveKw(){
  const r=await jpost("/v/api/ext/junk-keywords", {keywords:KWS});
  if(r.code===0){KWS=r.data.junk_keywords;CFG.junk_keywords=KWS.slice();renderKw();toast("关键词已保存");}
  else toast(r.msg||"保存失败","fail");
}
async function addKw(){
  const v=$("kwAdd").value.trim();if(!v)return;
  v.split(/[,，、\s]+/).filter(Boolean).forEach(k=>{if(!KWS.includes(k))KWS.push(k);});
  $("kwAdd").value="";await saveKw();
}
function toggleKwEdit(){const box=$("kwEdit");const show=box.style.display==="none";
  box.style.display=show?"block":"none";if(show)$("kwArea").value=KWS.join("\n");}
async function applyKwText(){
  KWS=$("kwArea").value.split(/[,，、\n\r;；\s]+/).map(s=>s.trim()).filter(Boolean).filter((k,i,a)=>a.indexOf(k)===i);
  $("kwEdit").style.display="none";await saveKw();
}
async function resetKw(){
  if(!confirm("恢复为默认关键词列表？"))return;
  const r=await jpost("/v/api/ext/junk-keywords", {reset:true});
  if(r.code===0){KWS=r.data.junk_keywords;CFG.junk_keywords=KWS.slice();renderKw();$("kwEdit").style.display="none";toast("已恢复默认");}
  else toast("失败","fail");
}
async function saveCfg(){
  const body={max_per_keyword:parseInt($("maxn").value)||12,filter_junk:$("junk").checked,online_first:$("onlineFirst").checked};
  const r=await jpost("/v/api/ext/config", body);
  if(r.code===0){toast("已保存");Object.assign(CFG,body);}else toast("保存失败 "+r.msg,"fail");
}
async function saveLines(){
  const body={line_fastest:$("lineFastest").checked,
    line_fastest_max:Math.max(2,Math.min(12,parseInt($("fastestMax").value)||6)),
    line_fastest_timeout:Math.max(1,Math.min(10,parseFloat($("fastestTimeout").value)||4)),
    line_autofail:$("lineAutofail").checked};
  const r=await jpost("/v/api/ext/config", body);
  if(r.code===0){toast("已保存");Object.assign(CFG,body);}else toast("保存失败 "+r.msg,"fail");
}
function initDanmu(){
  if(!CFG)return;
  $("danmuEnabled").checked=!!CFG.danmu_enabled;
  $("danmuAuto").checked=CFG.danmu_auto!==false;
  $("danmuApi").value=CFG.danmu_api||"";
  $("danmuToken").value=CFG.danmu_token||"";
  $("danmuOffset").value=CFG.danmu_offset==null?0:CFG.danmu_offset;
  $("danmuLimit").value=CFG.danmu_limit||800;
}
async function saveDanmu(){
  const body={danmu_enabled:$("danmuEnabled").checked,
    danmu_auto:$("danmuAuto").checked,
    danmu_api:$("danmuApi").value.trim(),
    danmu_token:$("danmuToken").value.trim(),
    danmu_offset:Math.max(-60,Math.min(60,parseFloat($("danmuOffset").value)||0)),
    danmu_limit:Math.max(100,Math.min(3000,parseInt($("danmuLimit").value)||800))};
  const r=await jpost("/v/api/ext/config", body);
  if(r.code===0){
    toast("已保存");Object.assign(CFG,body);
    $("danmuMsg").textContent=(body.danmu_enabled&&body.danmu_api)
      ?"已启用，下次进入播放页生效。":"已保存（未启用或未填写接口地址）。";
  }else toast("保存失败 "+(r.msg||""),"fail");
}
function initAdFilter(){
  $("adFilterEnabled").checked=!!(CFG&&CFG.ad_filter_enabled);
}
async function saveAdFilter(){
  const body={ad_filter_enabled:$("adFilterEnabled").checked};
  const r=await jpost("/v/api/ext/config", body);
  if(r.code===0){
    toast("已保存");Object.assign(CFG,body);
    $("adFilterMsg").textContent=body.ad_filter_enabled
      ?"已开启，下次起播生效。判断不确定的分片会保留，不影响正片。"
      :"已关闭，播放列表不再过滤。";
  }else toast("保存失败 "+(r.msg||""),"fail");
}
async function testDanmu(){
  const m=$("danmuMsg");m.textContent="测试中…";
  try{
    const r=await jpost("/v/api/ext/danmu/test", {api:$("danmuApi").value.trim(),token:$("danmuToken").value.trim()});
    m.textContent=(r.data&&r.data.msg)||r.msg||"完成";
  }catch(e){m.textContent="测试失败："+e;}
}
async function loadOnline(){
  const kw=$("kw").value.trim();
  const r=await jget("/v/api/ext/online?limit=500"+(kw?("&q="+encodeURIComponent(kw)):""));
  const list=r.data||[];$("cacheN").textContent=list.length;
  const tb=$("rows");
  if(!list.length){tb.innerHTML='<tr><td colspan="3" class="muted">暂无，先去飞牛搜索任意中文片名</td></tr>';return;}
  tb.innerHTML=list.map(x=>`<tr><td><div style="font-weight:500">${esc(x.title)}</div>
    <div class="meta">${esc(x.year||"")} ${esc(x.area||"")} · ${esc(x.remarks||"")}</div></td>
    <td>${esc(x.provider)}</td><td>${x.episodes}</td></tr>`).join("");
}



/* ---------- 初始化 ---------- */
async function loadStatus(){
  STATUS=await jget("/v/api/ext/status");
  CFG=STATUS.config;
  PRIO=STATUS.source_priority||{};
}
async function init(){
  await loadStatus();
  // 状态先落定：后续任何渲染异常都不应把「接口正常」误报成「未接管」
  const ver=STATUS.version||"__TMO_VERSION__";
  const gs=$("globalState"),gv=$("globalVer"),gm=$("globalMode");
  if(gv)gv.textContent=ver;
  const ovv=$("ovVer");if(ovv)ovv.textContent="v"+ver;
  if(gs){gs.textContent="服务正常 · 已缓存 "+(STATUS.cached_titles||0);gs.className="dot ok";}
  if(gm)gm.textContent=STATUS.takeover?"影视接口已接管":"接口直连（未接管）";
  const ed=$("aboutEdition");if(ed)ed.textContent="v"+ver+" · "+(FEAT_DDUO?"完整版（本地全功能）":"公开版")+" · 在飞牛原生搜索与媒体库中注入在线影视";
  try{
    KWS=Array.isArray(CFG.junk_keywords)?CFG.junk_keywords.slice():[];
    $("maxn").value=CFG.max_per_keyword;
    $("junk").checked=CFG.filter_junk;
    $("onlineFirst").checked=CFG.online_first!==false;
    $("lineFastest").checked=CFG.line_fastest!==false;
    $("lineAutofail").checked=CFG.line_autofail!==false;
    $("fastestMax").value=CFG.line_fastest_max||6;
    $("fastestTimeout").value=CFG.line_fastest_timeout||4;
    renderKw();renderSources();initDanmu();initAdFilter();
    try{loadLunaStatus();}catch(e){}
    loadOnline();
    renderOverview();
    loadLibs().then(renderLibrary).catch(e=>console.error(e));
  }catch(e){console.error(e);}
}
$("kwAdd").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();addKw();}});
$("kw").addEventListener("input",()=>{clearTimeout(window._t);window._t=setTimeout(loadOnline,250);});
init().catch(e=>{const gs=$("globalState"),gm=$("globalMode");
  if(gs){gs.textContent="管理接口未连接";gs.className="dot bad";}
  if(gm)gm.textContent="请从应用中心打开";console.error(e);});
</script>
</body>
</html>
"""
