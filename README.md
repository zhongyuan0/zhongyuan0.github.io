# zhongyuan0.github.io

孙中源（Zhongyuan Sun）的个人学术主页：<https://zhongyuan0.github.io>

网站是纯 HTML + CSS，没有构建步骤、没有插件。改完文字提交到 `main` 分支，GitHub Actions 会在一两分钟内自动发布（发布到 `gh-pages` 分支，GitHub Pages 的设置不用动）。

## 文件在哪里

| 想改什么 | 改这个文件 |
| --- | --- |
| 首页：自我介绍、三个研究方向（真善美）、News、代表作、联系方式 | `index.html` |
| Research 页：全部论文、在审、在写 | `research/index.html` |
| CV 页（网页版简历） | `cv/index.html` |
| 照片 | `assets/img/portrait.*`（桌面端，4:5 竖图）和 `assets/img/portrait-wide.*`（手机端） |
| 颜色、字号、版式 | `assets/css/site.css` 顶部的 Tokens |

## 常见操作

**加一条 News**：在 `index.html` 里找到 `<h3>2026</h3>`，在下面的 `<ul>` 里复制一行 `<li>…</li>` 改文字即可。新的一年就复制整个 `<div class="news-year">…</div>` 块。

**加一篇论文**：在审和在写的论文只写简短的主题，不写完整标题。在 `research/index.html` 对应栏目里复制一个 `<li>…</li>` 块，改标题、作者、期刊和 DOI 链接。作者里自己的名字用 `<span class="me">Zhongyuan Sun</span>` 包起来会稍微加深显示。获奖信息用 `<p class="pub-award">…</p>`。
同时记得在 `cv/index.html` 的 Publications 里加上同一篇（CV 用 APA 格式）。如果是代表作，也可以放进首页的 Selected publications。

**CV 的 PDF**：目前网站上不放 PDF。以后想放的话，把 PDF 上传到 `assets/pdf/`，再在 `index.html` 的链接列表和 `cv/index.html` 顶部加一个下载链接即可。在浏览器里打开 CV 页按「打印 → 另存为 PDF」可以得到排好版的 PDF。

**换照片**：把新照片按同样文件名放进 `assets/img/`。桌面端显示为 4:5 竖图，手机端显示原比例。

页脚的 “Last updated” 日期在四个 HTML 文件底部，大改之后可以顺手更新。

## 字体

正文是 Crimson Pro；竖排的「孙中源」和研究方向前的「真善美」用的是思源宋体（Noto Serif CJK SC），字体文件里只含这六个字。字体文件都放在网站本身（`assets/fonts/`），不依赖 Google Fonts，所以在中国大陆也能正常加载。授权见 `assets/fonts/NOTICE.txt`。
