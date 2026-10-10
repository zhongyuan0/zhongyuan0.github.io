# zhongyuan0.github.io

孙中源（Zhongyuan Sun）的个人学术主页：<https://zhongyuan0.github.io>

网站是纯 HTML + CSS，没有构建步骤、没有插件。改完文字提交到 `main` 分支，GitHub Actions 会在一两分钟内自动发布（发布到 `gh-pages` 分支，GitHub Pages 的设置不用动）。

## 文件在哪里

| 想改什么 | 改这个文件 |
| --- | --- |
| 首页：自我介绍、研究兴趣、News、代表作、联系方式 | `index.html` |
| Research 页：全部论文、在审、在写 | `research/index.html` |
| CV 页（网页版简历） | `cv/index.html` |
| CV 的 PDF | `assets/pdf/Zhongyuan_Sun_CV.pdf` |
| 照片 | `assets/img/portrait.*`（桌面端，4:5 竖图）和 `assets/img/portrait-wide.*`（手机端） |
| 颜色、字号、版式 | `assets/css/site.css` 顶部的 Tokens |

## 常见操作

**加一条 News**：在 `index.html` 里找到 `<h3>2026</h3>`，在下面的 `<ul>` 里复制一行 `<li>…</li>` 改文字即可。新的一年就复制整个 `<div class="news-year">…</div>` 块。

**加一篇论文**：在 `research/index.html` 对应栏目里复制一个 `<li>…</li>` 块，改标题、作者、期刊和 DOI 链接。作者里自己的名字用 `<span class="me">Zhongyuan Sun</span>` 包起来会稍微加深显示。获奖信息用 `<p class="pub-award">…</p>`。
同时记得在 `cv/index.html` 的 Publications 里加上同一篇（CV 用 APA 格式）。如果是代表作，也可以放进首页的 Selected publications。

**更新 CV 的 PDF**：直接用你自己导出的 PDF 覆盖 `assets/pdf/Zhongyuan_Sun_CV.pdf`（文件名保持不变，链接就不用改）。现在这份是由网页版 CV 打印生成的；在浏览器里打开 CV 页按「打印 → 另存为 PDF」也能得到同样排版的 PDF。

**换照片**：把新照片按同样文件名放进 `assets/img/`。桌面端显示为 4:5 竖图，手机端显示原比例。

页脚的 “Last updated” 日期在四个 HTML 文件底部，大改之后可以顺手更新。

## 字体

正文是 Crimson Pro，竖排的「孙中源」用的是思源宋体（Noto Serif CJK SC）只含这三个字的子集。字体文件都放在网站本身（`assets/fonts/`），不依赖 Google Fonts，所以在中国大陆也能正常加载。授权见 `assets/fonts/NOTICE.txt`。
