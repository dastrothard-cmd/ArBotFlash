const byId = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[character]));
const state = { overview:null, rows:[] };

async function request(url, options={}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `${response.status} ${response.statusText}`);
  return payload;
}

function message(text, error=false) {
  byId('message').textContent = text;
  byId('message').style.color = error ? 'var(--danger)' : 'var(--accent)';
}

async function loadOverview() {
  const payload = await request('/api/admin/overview');
  state.overview = payload;
  const cards = byId('overview').querySelectorAll('strong');
  [payload.meta.taxonCount,payload.meta.enrichedTaxa,payload.meta.licensedMediaCount,
   payload.meta.locallyStoredMediaCount,payload.meta.profileShellCount,payload.meta.packCount,
   payload.meta.reviewDecisionCount].forEach((value,index)=>cards[index].textContent=value);
  byId('warning').textContent = payload.sourceWarning;
  byId('writeMode').textContent = payload.writeModeConfigured
    ? 'Write mode is configured. Decisions still require the correct token.'
    : 'Read-only mode. The server has no ARBOTFLASH_ADMIN_TOKEN configured.';
}

function renderRows() {
  byId('queueCount').textContent = state.rows.length;
  byId('queue').innerHTML = state.rows.map((row,index)=>`<tr>
    <td><strong>${escapeHtml(row.common_name)}</strong><em>${escapeHtml(row.scientific_name)}</em></td>
    <td><strong>${escapeHtml(row.source_title)}</strong><small>${escapeHtml(row.source_key)}</small></td>
    <td><span class="status ${escapeHtml(row.status)}">${escapeHtml(row.status.replaceAll('_',' '))}</span><small>${row.checked_at ? `<br>${escapeHtml(row.checked_at)}` : ''}</small></td>
    <td><strong>${escapeHtml(row.proposed_scientific_name || 'No candidate yet')}</strong><small>${escapeHtml(row.proposed_rank || '')}${row.proposed_external_id ? ` · ID ${escapeHtml(row.proposed_external_id)}` : ''}${row.confidence !== null ? ` · confidence ${escapeHtml(row.confidence)}` : ''}</small></td>
    <td><small>${escapeHtml(row.notes || 'No evidence notes attached.')}</small></td>
    <td><div class="decision">
      <textarea data-rationale="${index}" placeholder="Decision rationale"></textarea>
      <div class="decision-actions">
        <button class="approve" data-decision="approve" data-index="${index}">Approve</button>
        <button class="reject" data-decision="reject" data-index="${index}">Reject</button>
        <button class="defer" data-decision="defer" data-index="${index}">Defer</button>
      </div>
      <small>${row.decision_count} previous decision${row.decision_count === 1 ? '' : 's'}</small>
    </div></td>
  </tr>`).join('') || '<tr><td colspan="6">No records match these filters.</td></tr>';
  byId('queue').querySelectorAll('[data-decision]').forEach(button=>button.addEventListener('click',()=>submitDecision(button)));
}

async function loadQueue() {
  message('Loading reconciliation queue…');
  const params = new URLSearchParams({limit:'500'});
  if (byId('statusFilter').value) params.set('status',byId('statusFilter').value);
  if (byId('sourceFilter').value) params.set('source',byId('sourceFilter').value);
  try {
    const payload = await request(`/api/admin/reconciliation?${params}`);
    state.rows = payload.items;
    renderRows();
    message(`Loaded ${payload.count} reconciliation records.`);
  } catch (error) { message(error.message,true); }
}

async function submitDecision(button) {
  const row = state.rows[Number(button.dataset.index)];
  const rationale = byId('queue').querySelector(`[data-rationale="${button.dataset.index}"]`).value.trim();
  const token = byId('adminToken').value;
  if (!rationale) { message('Add a rationale before recording a decision.',true); return; }
  try {
    const payload = await request(`/api/admin/reconciliation/${encodeURIComponent(row.taxon_id)}/${encodeURIComponent(row.source_key)}/decision`,{
      method:'POST',
      headers:{'Content-Type':'application/json','X-ArbotFlash-Admin-Token':token},
      body:JSON.stringify({decision:button.dataset.decision,rationale,reviewer:'ArbotFlash review workspace'})
    });
    message(`${row.scientific_name}: ${payload.previousStatus} → ${payload.status}`);
    await Promise.all([loadOverview(),loadQueue()]);
  } catch (error) { message(error.message,true); }
}

byId('refresh').addEventListener('click',()=>Promise.all([loadOverview(),loadQueue()]));
byId('statusFilter').addEventListener('change',loadQueue);
byId('sourceFilter').addEventListener('change',loadQueue);
Promise.all([loadOverview(),loadQueue()]).catch(error=>message(error.message,true));
