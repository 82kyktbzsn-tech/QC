(() => {
  const root = document.querySelector('#academic-data-qc');
  if (!root) return;

  const form = root.querySelector('#qc-form');
  const businessType = root.querySelector('#business-type');
  const classinfoFiles = [...root.querySelectorAll('.classinfo-file input')];
  const submitButton = root.querySelector('#start-button');
  const errorMessage = root.querySelector('#error-message');
  const resultSection = root.querySelector('#result-section');
  const resultTitle = root.querySelector('#result-title');
  const resultSummary = root.querySelector('#result-summary');
  const downloadButton = root.querySelector('#download-button');
  const historyMessage = root.querySelector('#history-message');
  const historyList = root.querySelector('#history-list');

  const apiBase = '/personalized/academic-data-qc/api';

  function setClassinfoVisibility() {
    const required = businessType.value === 'class';
    classinfoFiles.forEach((input) => {
      input.required = required;
      input.closest('.classinfo-file').hidden = !required;
    });
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = !message;
  }

  function formatJob(job) {
    const details = [
      `${job.business_label || job.business_type}`,
      job.selected_department,
      job.qc_month,
      job.status,
    ];
    return details.join(' · ');
  }

  function renderHistory(jobs) {
    historyList.replaceChildren();
    if (!jobs.length) {
      historyMessage.textContent = '暂无历史任务';
      return;
    }
    historyMessage.textContent = '服务端权威任务记录';
    jobs.forEach((job) => {
      const item = document.createElement('div');
      item.className = 'qc-history-item';
      item.textContent = formatJob(job);
      if (job.download_url) {
        const link = document.createElement('a');
        link.href = job.download_url;
        link.textContent = ' 下载结果';
        item.append(' · ', link);
      }
      historyList.append(item);
    });
  }

  async function refreshHistory() {
    try {
      const response = await fetch(`${apiBase}/data`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '历史任务读取失败');
      renderHistory(payload.data || []);
    } catch (error) {
      historyMessage.textContent = error.message;
    }
  }

  function renderResult(job) {
    resultTitle.textContent = `${job.selected_department} · ${job.business_label}质检结果`;
    resultSummary.replaceChildren();
    [
      `班级信息：${job.classinfo_checked ? job.classinfo_rows : '未检查'}`,
      `配课表：${job.schedule_rows || 0}`,
      `班级信息异常：${job.classinfo_checked ? job.classinfo_abnormal_rows : '无需班级信息'}`,
      `配课表异常：${job.schedule_abnormal_rows || 0}`,
    ].forEach((text) => {
      const item = document.createElement('div');
      item.className = 'qc-summary-item';
      item.textContent = text;
      resultSummary.append(item);
    });
    downloadButton.href = job.download_url;
    resultSection.hidden = false;
  }

  businessType.addEventListener('change', setClassinfoVisibility);
  setClassinfoVisibility();

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    showError('');
    submitButton.disabled = true;
    submitButton.textContent = '质检运行中…';
    try {
      const response = await fetch(`${apiBase}/jobs`, {
        method: 'POST',
        body: new FormData(form),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '质检运行失败');
      renderResult(payload);
      await refreshHistory();
    } catch (error) {
      showError(error.message);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = '开始质检';
    }
  });

  refreshHistory();
})();
