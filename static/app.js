const form = document.querySelector('#summary-form');
const urlInput = document.querySelector('#url-input');
const summaryLimitInput = document.querySelector('#summary-limit-input');
const submitButton = document.querySelector('#submit-button');
const status = document.querySelector('#status');
const results = document.querySelector('#results');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  await summarize(urlInput.value, Number(summaryLimitInput.value || 400));
});

async function summarize(url, maxSummaryLength) {
  setLoading(true);
  status.textContent = '正在抓取网页并用 Trafilatura 提取正文...';

  try {
    const response = await fetch('/api/summarize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url, maxSummaryLength }),
    });

    const payload = await parseApiResponse(response);
    if (!response.ok) {
      throw new Error(payload.detail || payload.error || '摘要失败');
    }

    render(payload);
    status.textContent = '摘要完成。';
  } catch (error) {
    results.classList.add('hidden');
    status.textContent = `出错了：${error.message}`;
  } finally {
    setLoading(false);
  }
}

function render(payload) {
  results.classList.remove('hidden');
  setText('#tool-name', payload.tool);
  setText('#title', payload.title);
  setText(
    '#meta',
    [payload.hostname, payload.author, payload.date].filter(Boolean).join(' / ') || '没有额外元数据'
  );
  renderPipeline(payload);
}

function setText(selector, value) {
  document.querySelector(selector).textContent = value;
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitButton.textContent = loading ? '处理中...' : '摘要';
}

async function parseApiResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return await response.json();
  }
  const text = await response.text();
  return { error: text || `HTTP ${response.status}` };
}

function renderPipeline(payload) {
  const root = document.querySelector('#pipeline-flow');
  const outputs = [payload.rawText, payload.cleanedText, payload.summary.join('\n\n')];
  const titles = ['原始抓取', '去噪 / 正文提取', '最终摘要'];

  root.innerHTML = payload.pipeline
    .map((stage, index) => {
      const open = stage.focus ? 'open' : '';
      const level = '';
      const body =
        index === 2
          ? `<pre class="summary-output">${escapeHtml(payload.summary.join('\n\n'))}</pre>`
          : `<textarea readonly>${escapeHtml(outputs[index] || '')}</textarea>`;

      return `
        <details class="flow-step ${level}" ${open}>
          <summary>
            <span class="flow-step-tag">${stage.step}</span>
            <span class="flow-step-title">${titles[index]}</span>
            <span class="flow-step-hint">${formatSize(getStepSize(payload, index))}</span>
          </summary>
          <div class="flow-step-body">
            ${body}
          </div>
        </details>
      `;
    })
    .join('');
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function getStepSize(payload, index) {
  if (index === 0) return payload.sizes.rawText;
  if (index === 1) return payload.sizes.cleanedText;
  return payload.sizes.summaryText;
}

function formatSize(size) {
  const kb = (size.bytes / 1024).toFixed(1);
  return `大小：${size.characters} chars / ${size.bytes} Bytes / ${kb} KB`;
}
