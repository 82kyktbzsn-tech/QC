const form = document.querySelector('#qc-form');
const scheduleInput = document.querySelector('#schedule');
const classinfoOpeningInput = document.querySelector('#classinfo-opening');
const classinfoSetupInput = document.querySelector('#classinfo-setup');
const classinfoClosingInput = document.querySelector('#classinfo-closing');
const classinfoInputs = [classinfoOpeningInput, classinfoSetupInput, classinfoClosingInput];
const qcMonthInput = document.querySelector('#qc-month');
const departmentSelect = document.querySelector('#standard-department');
const customDepartmentInput = document.querySelector('#custom-department');
const businessInputs = [...document.querySelectorAll('input[name="business_type"]')];
const taskContent = document.querySelector('#task-content');
const classinfoGroup = document.querySelector('#classinfo-group');
const uploadGrid = document.querySelector('#upload-grid');
const startButton = document.querySelector('#start-button');
const progressSection = document.querySelector('#progress-section');
const errorSection = document.querySelector('#error-section');
const resultSection = document.querySelector('#result-section');
const qcMonthScope = document.querySelector('#qc-month-scope');
const departmentHelp = document.querySelector('#department-help');
const progressDetail = document.querySelector('#progress-detail');
const scheduleMeta = document.querySelector('#schedule-box .file-meta');

const CLASS_DEPARTMENTS = [
  '小学学习机', '中学学习机', '高中班级部', '素养', '素质',
  '创新', '国外考试部', '青少部', '未标化',
];
const PREMIUM_DEPARTMENTS = ['高中一对一部', '国外考试部', '素养智学部'];

const systemDate = new Date();
qcMonthInput.value = (
  `${systemDate.getFullYear()}-${String(systemDate.getMonth() + 1).padStart(2, '0')}`
);
qcMonthInput.addEventListener('input', refreshQcMonthScope);
qcMonthInput.addEventListener('change', refreshQcMonthScope);
refreshQcMonthScope();

function getBusinessType() {
  return businessInputs.find(input => input.checked)?.value || '';
}

function getSelectedDepartment() {
  return departmentSelect.value === '__custom__'
    ? customDepartmentInput.value.trim()
    : departmentSelect.value;
}

function classinfoIsRequired() {
  return getBusinessType() === 'class';
}

function fillDepartments(businessType) {
  const departments = businessType === 'premium'
    ? PREMIUM_DEPARTMENTS
    : CLASS_DEPARTMENTS;
  departmentSelect.innerHTML = [
    '<option value="">请选择负责的部门</option>',
    ...departments.map(name => `<option value="${name}">${name}</option>`),
    '<option value="__custom__">其他部门（手动输入）</option>',
    '<option value="全部部门">全部部门（管理员）</option>',
  ].join('');
}

function refreshDepartmentSelection() {
  const isCustom = departmentSelect.value === '__custom__';
  customDepartmentInput.classList.toggle('hidden', !isCustom);
  customDepartmentInput.required = isCustom;
  if (!isCustom) customDepartmentInput.value = '';

  const department = getSelectedDepartment();
  if (departmentSelect.value === '全部部门') {
    departmentHelp.textContent = '管理员视图：结果将包含全部部门。';
  } else if (isCustom) {
    departmentHelp.textContent = '请输入与上传数据中完全一致的部门名称。';
  } else if (department) {
    departmentHelp.textContent = classinfoIsRequired()
      ? `班级信息和配课表都只展示“${department}”。`
      : `PCLV 配课表只展示“${department}”。`;
  } else {
    departmentHelp.textContent = classinfoIsRequired()
      ? '一次选择，同时用于班级信息和配课表。'
      : '本次只检查所选部门的 PCLV 配课表。';
  }
  invalidateExistingResult();
  refreshReadyState();
}

function refreshBusinessSelection() {
  const businessType = getBusinessType();
  taskContent.classList.toggle('hidden', !businessType);
  if (!businessType) return;

  fillDepartments(businessType);
  customDepartmentInput.value = '';
  customDepartmentInput.classList.add('hidden');
  customDepartmentInput.required = false;
  scheduleInput.value = '';

  const isPremium = businessType === 'premium';
  classinfoGroup.classList.toggle('hidden', isPremium);
  uploadGrid.classList.toggle('premium-only', isPremium);
  classinfoInputs.forEach(input => { input.required = !isPremium; });
  document.querySelector('#upload-requirement').textContent = isPremium
    ? '仅需 1 份 PCLV 高端配课表'
    : '准备 1 份班级配课表和 3 份班级信息';
  document.querySelector('#upload-guidance').textContent = isPremium
    ? '高端业务不检查班级信息。'
    : '同一次部门选择覆盖两类质检数据。';
  document.querySelector('#schedule-upload-title').textContent = isPremium
    ? '上传 PCLV 高端配课表'
    : '上传班级配课表';
  scheduleMeta.dataset.placeholder = isPremium
    ? '仅支持 PCLV 高端配课表'
    : '仅支持班级配课表（classlesson）';
  refreshScheduleUpload();
  refreshDepartmentSelection();
}

function invalidateExistingResult() {
  resultSection.classList.add('hidden');
  document.querySelector('#download-button').href = '#';
}

function refreshQcMonthScope() {
  const value = qcMonthInput.value;
  if (!value) {
    qcMonthScope.textContent = '请选择月份，系统不会默认使用当前月。';
  } else {
    const [year, month] = value.split('-').map(Number);
    const lastDay = new Date(year, month, 0).getDate();
    qcMonthScope.textContent = `月份规则截止 ${value}-${lastDay}；0人班检查起始 ${value}-01`;
  }
  invalidateExistingResult();
  refreshReadyState();
}

function formatNumber(value) {
  return new Intl.NumberFormat('zh-CN').format(value || 0);
}

function bindUpload(input, box) {
  const meta = box.querySelector('.file-meta');
  const button = box.querySelector('.select-button');
  const update = () => {
    const file = input.files[0];
    if (file) {
      meta.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
      box.classList.add('ready');
      button.textContent = '更换文件';
    } else {
      meta.textContent = meta.dataset.placeholder;
      box.classList.remove('ready');
      button.textContent = '选择文件';
    }
    invalidateExistingResult();
    refreshReadyState();
  };

  input.addEventListener('change', update);
  button.addEventListener('click', event => {
    event.preventDefault();
    input.click();
  });
  ['dragenter', 'dragover'].forEach(name => box.addEventListener(name, event => {
    event.preventDefault();
    box.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach(name => box.addEventListener(name, event => {
    event.preventDefault();
    box.classList.remove('dragging');
  }));
  box.addEventListener('drop', event => {
    if (event.dataTransfer.files.length) {
      input.files = event.dataTransfer.files;
      update();
    }
  });
  return update;
}

const refreshScheduleUpload = bindUpload(scheduleInput, document.querySelector('#schedule-box'));

function bindFileRow(input, box) {
  const meta = box.querySelector('small');
  const button = box.querySelector('.row-button');
  const update = () => {
    const file = input.files[0];
    if (file) {
      meta.textContent = file.name;
      box.classList.add('ready');
      button.textContent = '更换';
    } else {
      meta.textContent = meta.dataset.placeholder;
      box.classList.remove('ready');
      button.textContent = '选择';
    }
    invalidateExistingResult();
    refreshReadyState();
  };
  input.addEventListener('change', update);
  button.addEventListener('click', event => {
    event.preventDefault();
    input.click();
  });
  ['dragenter', 'dragover'].forEach(name => box.addEventListener(name, event => {
    event.preventDefault();
    box.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach(name => box.addEventListener(name, event => {
    event.preventDefault();
    box.classList.remove('dragging');
  }));
  box.addEventListener('drop', event => {
    if (event.dataTransfer.files.length) {
      input.files = event.dataTransfer.files;
      update();
    }
  });
}

bindFileRow(classinfoOpeningInput, document.querySelector('#classinfo-opening-box'));
bindFileRow(classinfoSetupInput, document.querySelector('#classinfo-setup-box'));
bindFileRow(classinfoClosingInput, document.querySelector('#classinfo-closing-box'));

businessInputs.forEach(input => input.addEventListener('change', refreshBusinessSelection));
departmentSelect.addEventListener('change', refreshDepartmentSelection);
customDepartmentInput.addEventListener('input', () => {
  invalidateExistingResult();
  refreshReadyState();
});

function refreshReadyState() {
  const completed = classinfoInputs.filter(input => input.files[0]).length;
  const status = document.querySelector('#classinfo-status');
  status.textContent = `${completed} / 3`;
  status.classList.toggle('complete', completed === 3);
  startButton.disabled = !(
    getBusinessType()
    && scheduleInput.files[0]
    && qcMonthInput.value
    && getSelectedDepartment()
    && (!classinfoIsRequired() || completed === 3)
  );
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const businessType = getBusinessType();
  const department = getSelectedDepartment();
  const selectedQcMonth = qcMonthInput.value;
  if (!businessType || !department || !selectedQcMonth) return;

  errorSection.classList.add('hidden');
  resultSection.classList.add('hidden');
  progressSection.classList.remove('hidden');
  const businessLabel = businessType === 'premium' ? '高端业务' : '班课业务';
  progressDetail.textContent = `正在处理 ${businessLabel} · ${department} · ${selectedQcMonth}，请保持页面打开。`;
  startButton.disabled = true;
  startButton.querySelector('span:first-child').textContent = '质检运行中';

  const data = new FormData();
  data.append('business_type', businessType);
  data.append('standard_department', department);
  data.append('schedule', scheduleInput.files[0]);
  if (classinfoIsRequired()) {
    data.append('classinfo_opening', classinfoOpeningInput.files[0]);
    data.append('classinfo_setup', classinfoSetupInput.files[0]);
    data.append('classinfo_closing', classinfoClosingInput.files[0]);
  }
  data.append('qc_month', selectedQcMonth);

  try {
    const response = await fetch('/api/qc', { method: 'POST', body: data });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || '质检运行失败');
    renderResult(payload);
  } catch (error) {
    document.querySelector('#error-message').textContent = error.message;
    errorSection.classList.remove('hidden');
  } finally {
    progressSection.classList.add('hidden');
    refreshReadyState();
    startButton.querySelector('span:first-child').textContent = '重新质检';
  }
});

function renderResult(data) {
  const department = data.selected_department;
  const classinfoTotal = document.querySelector('#classinfo-total');
  const classinfoAbnormal = document.querySelector('#classinfo-abnormal');
  if (data.classinfo_checked) {
    classinfoTotal.textContent = formatNumber(data.classinfo_rows);
    setAbnormal('#classinfo-abnormal', data.classinfo_abnormal_rows);
  } else {
    classinfoTotal.textContent = '未检查';
    classinfoAbnormal.textContent = '无需班级信息';
    classinfoAbnormal.classList.remove('alert');
  }
  document.querySelector('#schedule-total').textContent = formatNumber(data.schedule_rows);
  setAbnormal('#schedule-abnormal', data.schedule_abnormal_rows);
  document.querySelector('#schedule-type').textContent = (
    data.schedule_type === 'pclv' ? 'PCLV 高端配课表' : '班级配课表'
  );
  document.querySelector('#qc-month-result').textContent = data.qc_month;
  document.querySelector('#department-result').textContent = department;
  document.querySelector('#result-title').textContent = `${department} · ${data.business_label}质检结果`;
  document.querySelector('#result-subtitle').textContent = data.classinfo_checked
    ? `班级信息和配课表均已按“${department}”筛选。`
    : `本次只检查“${department}”的 PCLV 配课表。`;
  document.querySelector('#completed-time').textContent = `${data.created_at.slice(11, 16)} 完成`;
  document.querySelector('#download-button').href = data.download_url;
  document.querySelector('#download-label').textContent = `下载${department}结果`;

  const summaryBody = document.querySelector('#summary-body');
  summaryBody.innerHTML = data.department_summary.map(row => {
    const rate = Number(row['异常率'] || 0);
    return `<tr>
      <td>${escapeHtml(row['数据类型'])}</td>
      <td>${escapeHtml(row['标化部门'])}</td>
      <td>${formatNumber(row['总记录数'])}</td>
      <td>${formatNumber(row['异常记录数'])}</td>
      <td><span class="rate-bar"><i style="width:${Math.min(rate * 100, 100)}%"></i></span>${(rate * 100).toFixed(1)}%</td>
    </tr>`;
  }).join('');

  const rules = data.rule_stats.filter(rule => rule.count > 0).sort((a, b) => b.count - a.count);
  const ruleList = document.querySelector('#rule-list');
  ruleList.innerHTML = rules.length
    ? rules.map(rule => `<div class="rule-item"><span>${escapeHtml(rule.rule)}</span><strong>${formatNumber(rule.count)}</strong></div>`).join('')
    : '<div class="empty-rules">本次没有规则命中异常</div>';

  resultSection.classList.remove('hidden');
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setAbnormal(selector, count) {
  const element = document.querySelector(selector);
  element.textContent = `${formatNumber(count)} 条异常`;
  element.classList.toggle('alert', count > 0);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
