# Python FastAPI Sumy Web Summary Demo

## 简介

这个 Demo 演示如何把 `Sumy` 做成一个可直接在网页里试的摘要器。

因为 Sumy 的核心是“摘要算法”，不是网页正文提取，所以这里前面补了一层 `Trafilatura` 负责清洗网页正文，再把正文交给 Sumy 的 `LexRank`。

## 快速开始

### 环境要求

- Python 3.11+

### 运行

```bash
cd /Users/peng.li/workspace/freewind-demos/python-fastapi-sumy-web-summary-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

浏览器打开 `http://127.0.0.1:8000`。

首次运行时程序会自动准备 `punkt`、`punkt_tab` 这些 NLTK 分句资源。

## 概念讲解

### 第一部分：Sumy 是摘要器，不是网页提取器

在 [app.py](/Users/peng.li/workspace/freewind-demos/python-fastapi-sumy-web-summary-demo/app.py:1) 里，正文清洗先走 Trafilatura：

```python
text = trafilatura.extract(
    downloaded,
    output_format="txt",
    include_comments=False,
    include_tables=False,
    favor_precision=True,
)
```

原因很简单：如果直接拿网页 HTML 去喂 Sumy，导航、页脚、侧栏这些噪音会严重影响结果。

### 第二部分：摘要由 LexRank 完成

真正的摘要逻辑是：

```python
parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
summarizer = LexRankSummarizer(Stemmer(LANGUAGE))
summarizer.stop_words = get_stop_words(LANGUAGE)
```

这里的 LexRank 属于经典抽取式摘要算法。

它会根据句子之间的相似度构图，再选出最有代表性的句子。跟前面的词频打分法相比，LexRank 更偏“句子之间的全局关系”。

## 完整示例

这个 demo 的页面依旧很轻：

- [templates/index.html](/Users/peng.li/workspace/freewind-demos/python-fastapi-sumy-web-summary-demo/templates/index.html:1)
- [static/app.js](/Users/peng.li/workspace/freewind-demos/python-fastapi-sumy-web-summary-demo/static/app.js:1)

用户输入 URL 后，后端返回：

- 清洗后的标题、作者、日期
- LexRank 生成的摘要句
- 对照用的关键句
- 正文全文

这样你就能直接观察 Sumy 的输出风格。

## 注意事项

- 这个 demo 当前把语言固定在英文 `LexRank` 路线，英文文章效果通常更稳定
- 中文网页也能跑，但 Sumy 的经典英文 tokenizer/stemmer 对中文不算理想
- 所以这个 demo 更适合用来观察“算法风格”，不是做多语言最优解

## 中文完整讲解

这个 demo 其实很能说明一个常见误区：很多人会把“网页摘要”当成一个单一功能，但实际上它经常至少要拆成两步。

第一步是网页正文提取，第二步才是摘要。

Sumy 只负责第二步，而且它在这一层很经典。你可以把它理解成一个“传统摘要算法工具箱”，里面有 LexRank、LSA 这类方法。这个 demo 为了简单，固定用了 LexRank，因为它是比较常见、也比较有代表性的经典算法。

所以这个 demo 适合你观察的是：

1. 不靠大模型时，经典摘要算法长什么样
2. 经典算法和“词频选句”相比，风格有什么不同
3. 如果前面正文提取做得好，后面的传统摘要其实已经能提供一个不错的预览
