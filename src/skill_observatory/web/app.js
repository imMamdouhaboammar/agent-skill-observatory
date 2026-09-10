// Agent Skill Observatory — Dashboard
// Copyright (c) 2026 Mamdouh Aboammar. Apache-2.0 License.
const state={items:[],stats:{}};
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));

function normalize(row){
  const score=row.score||{};
  return {...row,
    overall_score:row.overall_score??score.overall??0,
    quality_score:row.quality_score??score.quality??0,
    security_score:row.security_score??score.security??0,
    maintenance_score:row.maintenance_score??score.maintenance??0,
    adoption_score:row.adoption_score??score.adoption??0,
    spec:row.spec||{},security:row.security||{},resources:row.resources||{}
  };
}

async function load(){
  try{
    const [skills,stats]=await Promise.all([fetch('/api/v1/skills?limit=200'),fetch('/api/v1/stats')]);
    if(!skills.ok||!stats.ok) throw new Error('API unavailable');
    const body=await skills.json(); state.items=body.items.map(normalize); state.stats=await stats.json();
    $('sourceStatus').textContent='Live API';
  }catch(_){
    const [skills,stats]=await Promise.all([fetch('./catalog.json'),fetch('./stats.json')]);
    state.items=(await skills.json()).map(normalize); state.stats=await stats.json();
    $('sourceStatus').textContent='Static catalog';
  }
  renderStats(); renderCategories(); renderClients(); render();
}

function renderCategories(){
  const categories=[...new Set(state.items.flatMap(x=>x.evidence?.categories||[]))].sort();
  $('category').innerHTML='<option value="">All</option>'+categories.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
}

function renderClients(){
  const clients=[...new Set(state.items.flatMap(x=>Object.keys(x.evidence?.client_compatibility_evidence||{})))].sort();
  const sel=$('client');
  if(sel) sel.innerHTML='<option value="">All clients</option>'+clients.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
}

function renderStats(){
  const entries=[['skills','Indexed skills'],['repositories','Repositories'],['spec_valid','Spec valid'],['security_85_plus','Security 85+'],['score_80_plus','Score 80+']];
  $('stats').innerHTML=entries.map(([k,l])=>`<div class="stat"><b>${Number(state.stats[k]||0).toLocaleString()}</b><span>${l}</span></div>`).join('');
}

function render(){
  const q=$('query').value.trim().toLowerCase(), min=+$('minScore').value, valid=$('validOnly').checked, safe=$('safeOnly').checked, category=$('category').value, sort=$('sort').value, clientSel=$('client')?.value||'';
  const items=state.items.filter(x=>(!q||`${x.name} ${x.repo_full_name} ${x.description}`.toLowerCase().includes(q))&&x.overall_score>=min&&(!valid||x.spec?.valid===true)&&(!safe||x.security_score>=85)&&(!category||(x.evidence?.categories||[]).includes(category))&&(!clientSel||Object.keys(x.evidence?.client_compatibility_evidence||{}).includes(clientSel)));
  const sorters={overall:(a,b)=>b.overall_score-a.overall_score,adoption:(a,b)=>b.adoption_score-a.adoption_score,security:(a,b)=>b.security_score-a.security_score,recent:(a,b)=>String(b.pushed_at).localeCompare(String(a.pushed_at))};
  items.sort(sorters[sort]||sorters.overall);
  $('resultCount').textContent=items.length; $('empty').hidden=items.length!==0;
  $('catalog').innerHTML=items.map((x,idx)=>card(x,idx)).join('');

  document.querySelectorAll('.card').forEach(el=>{
    el.setAttribute('tabindex','0');
    el.setAttribute('role','button');
    const handler=e=>{
      if(e.target.closest('a')) return;
      const idx=el.dataset.index;
      if(idx!==undefined&&items[idx]) showDetail(items[idx]);
    };
    el.addEventListener('click',handler);
    el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();handler(e);}});
  });
}

function card(x,idx){
  const findings=x.security?.findings?.length||0, valid=x.spec?.valid===true;
  const manifest=x.evidence?.manifest||`${x.repo_url}/tree/${x.repo_default_branch||'main'}/${x.path}`;
  const clients=Object.keys(x.evidence?.client_compatibility_evidence||{});
  const clientTags=clients.slice(0,3).map(c=>`<span class="tag">${esc(c)}</span>`).join('');
  return `<article class="card" data-index="${idx}" aria-label="${esc(x.name)} skill"><div><a href="${esc(manifest)}" target="_blank" rel="noreferrer" onclick="event.stopPropagation()"><h2>${esc(x.name)}</h2></a><div class="repo">${esc(x.repo_full_name)} · ${esc(x.path)}</div><p class="desc">${esc(x.description)}</p><div class="tags"><span class="tag ${valid?'good':'risk'}">${valid?'spec valid':'spec issues'}</span><span class="tag ${findings?'risk':'good'}">${findings?`${findings} safety findings`:'verified clean'}</span><span class="tag">★ ${Number(x.stars||0).toLocaleString()}</span>${x.license?`<span class="tag">${esc(x.license)}</span>`:''}<span class="tag">${x.resources?.scripts||0} scripts</span>${(x.evidence?.categories||[]).slice(0,2).map(c=>`<span class="tag">${esc(c)}</span>`).join('')}${clientTags}</div></div><div class="scores"><div class="score overall"><b>${x.overall_score}</b><span>Overall</span></div><div class="score"><b>${x.quality_score}</b><span>Quality</span></div><div class="score"><b>${x.security_score}</b><span>Security</span></div><div class="score"><b>${x.maintenance_score}</b><span>Maintenance</span></div><div class="score"><b>${x.adoption_score}</b><span>Adoption</span></div></div></article>`;
}

function copyScanCmd(path,btn){
  const cmd=`skillobs scan-local ${path}`;
  navigator.clipboard.writeText(cmd).then(()=>{
    const orig=btn.textContent; btn.textContent='✓ Copied!'; btn.disabled=true;
    setTimeout(()=>{btn.textContent=orig; btn.disabled=false;},2000);
  }).catch(()=>{
    // Fallback: select text from a temporary textarea
    const ta=document.createElement('textarea'); ta.value=cmd; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
    const orig=btn.textContent; btn.textContent='✓ Copied!'; setTimeout(()=>btn.textContent=orig,2000);
  });
}

function showDetail(x){
  const modal=$('detailModal');
  $('modalTitle').textContent=x.name;
  const findings=x.security?.findings||[];
  const manifest=x.evidence?.manifest||`${x.repo_url}/blob/${x.repo_default_branch||'main'}/${x.path}`;
  const clients=Object.keys(x.evidence?.client_compatibility_evidence||{}).join(', ')||x.compatibility||'Universal';

  $('modalBody').innerHTML=`
    <div class="modal-repo"><a href="${esc(x.repo_url)}" target="_blank" rel="noreferrer">${esc(x.repo_full_name)}</a> <span>(${esc(x.path)})</span></div>
    <p class="modal-desc">${esc(x.description)}</p>
    <div class="modal-meta-grid">
      <div><strong>License:</strong> ${esc(x.license||'None')}</div>
      <div><strong>Compatibility:</strong> ${esc(clients)}</div>
      <div><strong>Stars:</strong> ${Number(x.stars||0).toLocaleString()}</div>
      <div><strong>Scripts:</strong> ${x.resources?.scripts||0}</div>
    </div>
    <div class="modal-scores">
      <div class="stat"><b>${x.overall_score}</b><span>Overall</span></div>
      <div class="stat"><b>${x.quality_score}</b><span>Quality</span></div>
      <div class="stat"><b>${x.security_score}</b><span>Security</span></div>
      <div class="stat"><b>${x.maintenance_score}</b><span>Maintenance</span></div>
      <div class="stat"><b>${x.adoption_score}</b><span>Adoption</span></div>
    </div>
    <div class="modal-section">
      <h3>Security Evidence</h3>
      ${findings.length===0
        ? '<div class="banner-clean">✓ Zero dangerous patterns flagged. Static scanner passed clean.</div>'
        : findings.map(f=>`
          <div class="finding-item">
            <span class="badge-severity ${esc(f.severity)}">${esc(f.severity.toUpperCase())}</span>
            <strong>${esc(f.rule)}</strong> — ${esc(f.message)}
            ${f.file?`<div class="finding-loc">${esc(f.file)}${f.line?`:${f.line}`:''}</div>`:''}
            ${f.evidence?`<code>${esc(f.evidence)}</code>`:''}
          </div>
        `).join('')}
    </div>
    <div class="modal-actions">
      <a href="${esc(manifest)}" target="_blank" rel="noreferrer" class="btn-primary">View Manifest on GitHub ↗</a>
      <button class="btn-secondary" id="copyScanBtn">📋 Copy Scan Command</button>
    </div>
  `;
  document.getElementById('copyScanBtn').addEventListener('click',function(){copyScanCmd(x.path,this);});
  modal.showModal();
  // Focus close button for accessibility
  setTimeout(()=>$('modalClose').focus(),50);
}

$('modalClose').addEventListener('click',()=>$('detailModal').close());
$('detailModal').addEventListener('click',e=>{if(e.target===$('detailModal')) $('detailModal').close();});

// Keyboard: Escape closes modal (native dialog behavior, but explicit fallback)
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&$('detailModal').open) $('detailModal').close();
});

['query','minScore','category','client','sort','validOnly','safeOnly'].forEach(id=>{
  const el=$(id); if(el) el.addEventListener(id==='query'?'input':'change',render);
});

load().catch(err=>{$('sourceStatus').textContent='Catalog unavailable';$('catalog').innerHTML=`<div class="empty">${esc(err.message)}</div>`;});
