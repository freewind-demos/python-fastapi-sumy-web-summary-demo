from __future__ import annotations

import re
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import nltk
import trafilatura
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, HttpUrl
from sumy.nlp.stemmers import Stemmer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.utils import get_stop_words


app = FastAPI(title="Sumy Web Summary Demo")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

LANGUAGE = "english"


class SummaryRequest(BaseModel):
    url: HttpUrl
    maxSummaryLength: int = Field(default=0)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "tool_name": "Sumy",
            "subtitle": "正文先交给 Trafilatura 清洗，再用 Sumy 的经典 LexRank 算法做摘要。",
            "hint": "这个 demo 的主角是 Sumy，所以页面里看到的摘要主要来自 LexRank。",
        },
    )


@app.post("/api/summarize")
async def summarize(payload: SummaryRequest) -> dict[str, Any]:
    ensure_nltk()

    downloaded = trafilatura.fetch_url(str(payload.url))
    if not downloaded:
        raise HTTPException(status_code=422, detail="没有抓到网页内容。")

    metadata = trafilatura.extract_metadata(downloaded)
    text = trafilatura.extract(
        downloaded,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )

    if not text or len(text.strip()) < 180:
        raise HTTPException(
            status_code=422,
            detail="Sumy demo 没有拿到足够正文。这里的正文清洗由 Trafilatura 提供。",
        )

    clean_text = compact_whitespace(text)
    extracted_object = {
        "metadata": {
            "title": metadata.title if metadata and metadata.title else "",
            "author": metadata.author if metadata and metadata.author else "",
            "date": metadata.date if metadata and metadata.date else "",
            "description": metadata.description if metadata and metadata.description else "",
            "url": str(payload.url),
        },
        "text": clean_text,
    }
    summary = limit_summary_length(summarize_with_sumy(clean_text, 4), payload.maxSummaryLength)
    highlights = split_sentences(clean_text)[:3]

    return {
        "tool": "Sumy + LexRank",
        "title": metadata.title if metadata and metadata.title else fallback_title(str(payload.url)),
        "author": metadata.author if metadata and metadata.author else "",
        "hostname": urlparse(str(payload.url)).hostname or "",
        "date": metadata.date if metadata and metadata.date else "",
        "description": metadata.description if metadata and metadata.description else "",
        "rawText": downloaded,
        "cleanedText": json_dump(extracted_object),
        "summary": summary,
        "highlights": highlights,
        "text": clean_text,
        "pipeline": [
            {
                "step": "1. 原始抓取",
                "core": "trafilatura.fetch_url",
                "helper": "项目内置 HTML 粗转文本",
                "detail": "先抓原始 HTML，并把整页文本粗略展开。这个阶段只是给你看原始网页到底有多脏。",
                "output": "产出：整页粗文本，主要作为对照。",
                "focus": False,
            },
            {
                "step": "2. 去噪 / 正文提取",
                "core": "Trafilatura",
                "helper": "extract_metadata 提供元数据",
                "detail": "Sumy 不是网页正文提取器，所以这里专门借 Trafilatura 先把正文洗出来。",
                "output": "产出：适合送进 Sumy 的正文文本。",
                "focus": False,
            },
            {
                "step": "3. 摘要",
                "core": "Sumy LexRank",
                "helper": "NLTK tokenizer + stop words",
                "detail": "这个 demo 的核心看点在这里。Sumy 根据句子相似度生成抽取式摘要，不依赖大模型。",
                "output": "产出：LexRank 摘要，这是当前 demo 的重点展示结果。",
                "focus": True,
            },
        ],
        "stats": {
            "characters": len(clean_text),
            "sentences": len(split_sentences(clean_text)),
            "summary_sentences": len(summary),
        },
        "sizes": {
            "rawText": measure_text(downloaded),
            "cleanedText": measure_text(json_dump(extracted_object)),
            "summaryText": measure_text("\n\n".join(summary)),
        },
    }


def summarize_with_sumy(text: str, sentence_count: int) -> list[str]:
    parser = PlaintextParser.from_string(text, Tokenizer(LANGUAGE))
    summarizer = LexRankSummarizer(Stemmer(LANGUAGE))
    summarizer.stop_words = get_stop_words(LANGUAGE)
    sentences = [str(sentence).strip() for sentence in summarizer(parser.document, sentence_count)]
    return sentences or split_sentences(text)[:sentence_count]


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def measure_text(text: str) -> dict[str, int]:
    return {
        "characters": len(text),
        "bytes": len(text.encode("utf-8")),
    }


def limit_summary_length(summary: list[str], max_length: int) -> list[str]:
    joined = "\n\n".join(summary).strip()
    if max_length <= 0:
        return summary
    if len(joined) <= max_length:
        return summary
    return [joined[:max_length].strip()]


def json_dump(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, indent=2)


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[。！？.!?])\s+", text)
        if len(sentence.strip()) > 20
    ]


def fallback_title(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or "Untitled page"


@lru_cache(maxsize=1)
def ensure_nltk() -> None:
    for resource, path in [
        ("punkt", "tokenizers/punkt"),
        ("punkt_tab", "tokenizers/punkt_tab"),
    ]:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(resource, quiet=True)
