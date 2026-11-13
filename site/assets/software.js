'use strict';
(() => {
  const data=JSON.parse(document.getElementById('software-data').textContent);
  const split=value=>(value||'').split(';').map(v=>v.trim()).filter(Boolean);
  const validURL=value=>{try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password&&!/\s/.test(value);}catch{return false;}};
  const normalizeDOI=value=>value.trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i,'').toLowerCase();
  const people=new Map(data.people.map(p=>[p.number,p]));
  const irpLabel=number=>{const p=people.get(number);return `IRP ${number}`+(p?' · '+(p.candidate?.name||p.short_title):'');};
  const paperNames=new Map([...data.papers.publications,...data.papers.working_papers].map(p=>[p.id,p.title]));
  const records=document.getElementById('records');
  function option(select,value,label){const node=document.createElement('option');node.value=value;node.textContent=label;select.append(node);}
  if(records){
    const mapping={category:'category',language:'languages',irp:'irp_numbers',data:'data_availability',index:'index'};
    const labels={category:data.categories,data:data.availability,index:data.indices};
    const controls=Object.keys(mapping),params=new URLSearchParams(location.search);
    const search=document.getElementById('search'),sort=document.getElementById('sort');
    search.value=params.get('q')||'';if(['name','updated'].includes(params.get('sort')))sort.value=params.get('sort');
    for(const name of controls){
      const select=document.getElementById(name+'-filter');
      const values=labels[name]?Object.keys(labels[name]):[...new Set(data.software.flatMap(row=>split(row[mapping[name]])))].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
      values.forEach(value=>option(select,value,name==='irp'?irpLabel(value):labels[name]?.[value]||value));
      if(params.has(name))select.value=params.get(name);
      select.addEventListener('change',render);
    }
    const chips=document.getElementById('category-chips');
    for(const [value,label] of [['','All software'],...Object.entries(data.categories)]){
      const button=document.createElement('button');button.type='button';button.className='software-chip';button.dataset.category=value;button.textContent=label;button.addEventListener('click',()=>{document.getElementById('category-filter').value=value;render();});chips.append(button);
    }
    const cards=new Map([...records.querySelectorAll('[data-record-id]')].map(card=>[card.dataset.recordId,card]));
    function render(){
      const filter=Object.fromEntries(controls.map(name=>[name,document.getElementById(name+'-filter').value]));
      const words=search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      const found=data.software.filter(row=>{
        const papers=[...split(row.publication_ids),...split(row.working_paper_ids)].map(id=>paperNames.get(id)||'');
        const text=[...Object.values(row),...papers].join(' ').toLowerCase();
        return words.every(word=>text.includes(word))&&controls.every(name=>!filter[name]||split(row[mapping[name]]).includes(filter[name]));
      }).sort((a,b)=>sort.value==='updated'?(b.last_updated||'').localeCompare(a.last_updated||'')||a.name.localeCompare(b.name):a.name.localeCompare(b.name));
      cards.forEach(card=>card.hidden=true);found.forEach(row=>{const card=cards.get(row.id);card.hidden=false;records.append(card);});
      document.getElementById('result-count').textContent=`${found.length} software ${found.length===1?'record':'records'}`;
      document.getElementById('empty').hidden=found.length>0;
      chips.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.category===filter.category)));
      const query=new URLSearchParams();if(search.value)query.set('q',search.value);controls.forEach(name=>{if(filter[name])query.set(name,filter[name]);});if(sort.value!=='name')query.set('sort',sort.value);
      history.replaceState(null,'',location.pathname+(query.size?'?'+query:'')+location.hash);
    }
    function reset(){search.value='';sort.value='name';controls.forEach(name=>document.getElementById(name+'-filter').value='');render();}
    search.addEventListener('input',render);sort.addEventListener('change',render);document.getElementById('reset').addEventListener('click',reset);
    document.addEventListener('click',async event=>{const button=event.target.closest('[data-copy]');if(!button)return;const url=new URL(location.href);url.hash=button.dataset.copy;try{await navigator.clipboard.writeText(url.href);button.textContent='Link copied';}catch{location.hash=button.dataset.copy;button.textContent='Copy the URL from your address bar';}});
    function route(){const match=location.hash.match(/^#software\/([a-z0-9-]+)$/);const card=match&&cards.get(match[1]);if(card){reset();card.querySelector('details').open=true;card.scrollIntoView({block:'start'});}}
    addEventListener('hashchange',route);render();route();
  }
  document.querySelectorAll('.software-figure img').forEach(img=>img.addEventListener('error',()=>{img.hidden=true;}));
  const form=document.getElementById('software-form');
  if(!form)return;
  const control=name=>form.elements.namedItem(name),status=document.getElementById('form-status'),review=document.getElementById('proposal-review');
  for(const p of people.values())option(control('irp_numbers'),p.number,irpLabel(p.number));
  for(const [field,kind] of [['publication_ids','publications'],['working_paper_ids','working_papers']]){data.papers[kind].forEach(p=>option(control(field),p.id,p.title));if(!data.papers[kind].length){option(control(field),'','No '+(kind==='working_papers'?'working papers':'publications')+' listed yet');control(field).lastElementChild.disabled=true;}}
  const params=new URLSearchParams(location.search),existing=data.software.find(row=>row.id===params.get('id'));
  function populate(record){for(const element of form.elements){if(!element.name||record[element.name]===undefined)continue;if(element.multiple)[...element.options].forEach(o=>o.selected=split(record[element.name]).includes(o.value));else element.value=record[element.name];}}
  if(existing){populate(existing);control('action').value='update';}else{control('last_updated').value=new Date().toISOString().slice(0,10);if(people.has(params.get('irp')))populate({irp_numbers:params.get('irp')});}
  let proposal;
  function sync(){control('index_url').required=control('index').value!=='not-indexed';control('key_image_alt').required=!!control('key_image_url').value;}
  function invalidate(){proposal=null;review.hidden=true;status.textContent='';sync();}
  form.addEventListener('input',invalidate);form.addEventListener('change',invalidate);sync();
  form.addEventListener('submit',event=>{
    event.preventDefault();const values=new FormData(form),record={};
    for(const [key,value] of values)if(!['action'].includes(key))record[key]=String(value).trim();
    for(const field of ['irp_numbers','publication_ids','working_paper_ids'])record[field]=values.getAll(field).join(';');
    for(const field of ['index_url','doi','key_image_url','key_image_alt','key_image_caption'])record[field]=record[field]||'';
    if(!record.id)record.id=record.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
    if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(record.id)){status.textContent='Enter an ID using lowercase letters, numbers and hyphens.';return;}
    const found=data.software.find(row=>row.id===record.id),action=control('action').value;
    if(action==='add'&&found||action==='update'&&!found){status.textContent='Choose an existing ID for an update, or a new ID for an addition.';return;}
    if(!record.publication_ids&&!record.working_paper_ids&&!split(record.paper_urls).length){status.textContent='Link a published paper, working paper, or external paper URL.';return;}
    for(const [key,value] of Object.entries(record))if(value&&key.endsWith('_url')&&!validURL(value)){status.textContent='Use public HTTP(S) links.';return;}
    if(split(record.paper_urls).some(url=>!validURL(url))){status.textContent='Use public HTTP(S) paper links separated with semicolons.';return;}
    if(record.paper_titles&&split(record.paper_titles).length!==split(record.paper_urls).length){status.textContent='Supply one title for each external paper URL, in the same order.';return;}
    if(record.index==='not-indexed'&&(record.index_url||record.doi)){status.textContent='Choose an index when supplying an index URL or software DOI.';return;}
    if(record.doi){record.doi=normalizeDOI(record.doi);if(!/^10\.\d{4,9}\/\S+$/.test(record.doi)||data.software.some(row=>normalizeDOI(row.doi||'')===record.doi&&row.id!==record.id)){status.textContent='Enter a valid, unique software DOI.';return;}}
    if(record.key_image_url&&!/\.(png|jpe?g|gif|webp)$/i.test(new URL(record.key_image_url).pathname)){status.textContent='Use a direct PNG, JPEG, GIF or WebP image URL.';return;}
    if(!record.key_image_url&&(record.key_image_alt||record.key_image_caption)){status.textContent='Provide an image URL for the image description or caption.';return;}
    proposal={kind:'software',action,record};document.getElementById('proposal-json').textContent=JSON.stringify(proposal,null,2);
    const body='## Software proposal\n\nPlease review before applying software-approved.\n\n```json\n'+JSON.stringify(proposal,null,2)+'\n```';
    const url=data.config.repository+'/issues/new?'+new URLSearchParams({template:'software-proposal.md',title:`[Software ${action}] ${record.name}`,body});
    const issue=document.getElementById('open-issue');issue.href=url;issue.hidden=url.length>7000;document.getElementById('long-proposal').hidden=url.length<=7000;
    const preview=document.getElementById('image-preview');preview.hidden=!record.key_image_url;if(record.key_image_url){preview.querySelector('img').src=record.key_image_url;preview.querySelector('img').alt=record.key_image_alt;preview.querySelector('figcaption').textContent=record.key_image_caption;}
    review.hidden=false;status.textContent='Proposal prepared. Review it, then submit the issue on GitHub.';review.scrollIntoView({block:'start'});
  });
  document.getElementById('download-json').addEventListener('click',()=>{if(!proposal)return;const url=URL.createObjectURL(new Blob([JSON.stringify(proposal,null,2)+'\n'],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='software-'+proposal.record.id+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  document.getElementById('save-draft').addEventListener('click',()=>{try{const draft={};for(const element of form.elements)if(element.name)draft[element.name]=element.multiple?[...element.selectedOptions].map(o=>o.value).join(';'):element.value;localStorage.setItem('digital-software-draft',JSON.stringify(draft));status.textContent='Draft saved in this browser.';}catch{status.textContent='This browser could not save the draft.';}});
  document.getElementById('restore-draft').addEventListener('click',()=>{try{const draft=JSON.parse(localStorage.getItem('digital-software-draft')||'null');if(!draft){status.textContent='No draft saved in this browser.';return;}populate(draft);invalidate();status.textContent='Draft restored. Review it before submitting.';}catch{status.textContent='This browser could not restore the draft.';}});
})();
