async function callAPI(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'API 응답을 확인하세요.');
  return data;
}
document.querySelector('#search-form').addEventListener('submit', async event => {
  event.preventDefault();
  const target = document.querySelector('#search-result');
  try {
    const params = new URLSearchParams({category:document.querySelector('#category').value,q:document.querySelector('#query').value});
    const data = await callAPI('/api/projects?' + params);
    target.replaceChildren();
    const count = document.createElement('p'); count.textContent = `${data.count}개 프로젝트`; target.append(count);
    for (const item of data.items) {
      const line = document.createElement('p'); line.textContent = `${item.title} (${item.category}) — ${item.description}`; target.append(line);
    }
  } catch(error) { target.textContent = error.message; }
});
document.querySelector('#analyze-form').addEventListener('submit', async event => {
  event.preventDefault();
  const target = document.querySelector('#analyze-result');
  try {
    const data = await callAPI('/api/analyze', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:document.querySelector('#intro').value})});
    target.textContent = `공백 포함 ${data.characters}자 / 공백 기준 ${data.words}단어 / 권장 ${data.minimum}~${data.maximum}자: ${data.within_range ? '충족' : '조정 필요'}`;
  } catch(error) { target.textContent = error.message; }
});
