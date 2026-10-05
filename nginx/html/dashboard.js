const $ = selector => document.querySelector(selector);
let polling = false;
const number = value => Number.isFinite(value) ? value.toLocaleString('ko-KR') : '—';

function showDashboard(data) {
  $('#rpm').textContent = number(data.requests_last_minute);
  $('#average-pods').textContent = number(data.current_replicas);
  $('#pod-average').textContent = number(data.current_average_requests_per_minute);
  $('#target').textContent = number(data.target_requests_per_minute);
  $('#rule-target').textContent = number(data.target_requests_per_minute);
  $('#rule-min').textContent = number(data.autoscaler?.min_replicas);
  $('#rule-max').textContent = number(data.autoscaler?.max_replicas);
  $('#total').textContent = number(data.total_requests);
  $('#latency').textContent = number(data.average_latency_ms);
  $('#recommended').textContent = number(data.recommended_replicas);
  $('#desired').textContent = number(data.desired_replicas);
  $('#current').textContent = number(data.current_replicas);
  $('#ready').textContent = number(data.ready_replicas);
  const endpoints = $('#endpoint-rows');
  endpoints.replaceChildren();
  for (const endpoint of data.endpoints || []) {
    const row = document.createElement('tr');
    for (const value of [endpoint.path, `${number(endpoint.requests_last_minute)}건`,
      `${number(endpoint.total_requests)}건`, `${number(endpoint.average_latency_ms)} ms`]) {
      const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
    }
    endpoints.append(row);
  }
  if (!endpoints.childElementCount) {
    const row = document.createElement('tr'), cell = document.createElement('td');
    cell.colSpan = 4; cell.textContent = '아직 기록된 API 요청이 없습니다.';
    row.append(cell); endpoints.append(row);
  }
  const conditions = data.autoscaler?.conditions || [];
  const inactive = conditions.find(item => ['AbleToScale', 'ScalingActive'].includes(item.type) && item.status === 'False');
  $('#hpa-status').textContent = inactive
    ? `확인 필요 · ${inactive.reason || inactive.type}`
    : data.ready_replicas === data.desired_replicas ? '설정한 수만큼 준비 완료' : 'Pod 수 조절·준비 중';
  const rows = $('#pod-rows');
  rows.replaceChildren();
  const pods = data.pods || [];
  if (!pods.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.textContent = '아직 확인된 Pod가 없습니다.';
    row.append(cell); rows.append(row);
  }
  for (const pod of pods) {
    const row = document.createElement('tr');
    const values = [pod.name, pod.ready ? '준비 완료' : (pod.phase || '준비 중'),
      `${number(pod.requests_last_minute)}건`, `${number(pod.total_requests)}건`, `${number(pod.average_latency_ms)} ms`];
    for (const value of values) {
      const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
    }
    rows.append(row);
  }
  const date = new Date(data.metrics_updated_at);
  const updated = Number.isNaN(date.valueOf()) ? '시간 확인 불가' : date.toLocaleTimeString('ko-KR');
  $('#connection').textContent = `연결됨 · 마지막 측정 ${updated} · 화면 2초마다 갱신`;
  $('#error').textContent = '';
}

async function poll() {
  if (polling) return;
  polling = true;
  try {
    const response = await fetch('/api/dashboard', {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '대시보드 응답 오류');
    showDashboard(data);
  } catch(error) {
    $('#connection').textContent = '현재 측정을 불러오지 못했습니다. 표시된 수치는 마지막 성공 결과입니다.';
    $('#error').textContent = `연결 확인: ${error.message}. API·metrics·HPA 상태를 확인하세요.`;
  } finally { polling = false; }
}
poll();
setInterval(poll, 2000);
