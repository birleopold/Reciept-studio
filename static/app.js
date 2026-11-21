const $ = s => document.querySelector(s);
const groups = [
 ['Delivery header', [['headline','Heading'],['phone_label','Phone label'],['phone1','First phone'],['phone2','Second phone']]],
 ['Business details', [['business','Business / branch'],['address','Address'],['tin','Business TIN'],['title','Receipt title'],['currency','Currency code']]],
 ['Invoice details', [['customer','Customer TIN / name'],['date','Date','date'],['number','Receipt number'],['invoice','Invoice number'],['verification','Verification code'],['fdn','FDN']]],
 ['Items', []],
 ['Payment breakdown', [['cash','Cash','number'],['card','Credit card','number'],['coupon','Coupon','number'],['mobile','Mobile money','number'],['loyalty','Loyalty','number'],['gift','Gift card','number'],['promo','Promo','number'],['tax_rate','Tax rate (%)','number'],['vat','VAT note']]],
 ['Delivery details', [['delivery_title','Section heading'],['recipient','Recipient name'],['area','Delivery address','textarea'],['delivery_phone','Delivery phone']]],
 ['QR code & footer', [['qr','QR code content / verification URL','textarea'],['airtel','Airtel instructions'],['momo','MoMo instructions'],['width','Paper width','select']]]
];
let timer, revision = 0, dirty = false, savedId = '', busy = false, historyQuery = '', nextBefore = null;
const draftKey = 'receipt-studio-draft-v1';
const profileKey = 'receipt-studio-profiles-v1';
const profileFields = ['headline','phone_label','phone1','phone2','business','address','tin','title','currency','vat','tax_rate','delivery_title','airtel','momo','width','logo'];
let issuedHtml = '', logo = '', currentReceipt, issueToken = '';
const issuedIds = new Set();
const readLocal = key => {
 try {return JSON.parse(localStorage.getItem(key));}
 catch {return null;}
};
function writeLocal(key, value) {
 try {localStorage.setItem(key, JSON.stringify(value));return true;}
 catch {return false;}
}
const discard = () => !dirty || confirm('Discard unsaved receipt changes?');
window.addEventListener('beforeunload', event => {
 if (dirty) {event.preventDefault(); event.returnValue = '';}
});
function field(key,label,type='text',value='') {
 const wrap=document.createElement('label'); wrap.textContent=label;
 const input=document.createElement(type==='textarea'?'textarea':type==='select'?'select':'input');
 input.name=key; input.id=key;
 if(type==='select') {for(const w of ['80','58']) {const o=new Option(w+' mm',w);input.add(o);}}
 else if(type!=='textarea') {input.type=type; if(type==='number'){input.min='0';input.step='any';}}
 input.value=value ?? ''; wrap.append(input); return wrap;
}
function build(d) {
 clearTimeout(timer);
 ++revision;
 currentReceipt=d; logo=d.logo || '';
 dirty=false; $('#fields').replaceChildren();
 for(const [title,fields] of groups){
  const section=document.createElement('details'); section.open=['Delivery header','Items'].includes(title);
  const summary=document.createElement('summary');summary.textContent=title;section.append(summary);
  const grid=document.createElement('div');grid.className='field-grid';
  for(const [key,label,type] of fields) grid.append(field(key,label,type,d[key]));
  if(title==='Items'){
   grid.className='items';grid.id='items';section.append(grid);
   const add=document.createElement('button');add.type='button';add.className='add-item';add.textContent='+ Add item';add.onclick=()=>{if ($('#items').children.length < 100) {addItem({name:'',qty:'1',price:'0'});changed();}};section.append(add);
  } else section.append(grid);
  if(title==='QR code & footer'){const note=document.createElement('p');note.className='hint';note.textContent='Enter your own QR content. Leave empty to hide it. Verification code and FDN are supplied by your invoicing system; this app does not issue them.';section.append(note);}
  $('#fields').append(section);
 }
 d.items.forEach(addItem);
 if (d.items.some(item => item.name.trim())) schedule();
 else {$('#preview').replaceChildren();status('Enter an item name to preview your receipt.');}
}
function addItem(item){
 const row=document.createElement('div');row.className='item';
 for(const [key,label,type] of [['name','Item name','text'],['qty','Qty','number'],['price','Unit price','number'],['discount','Line discount','number']]){
  const f=field(key,label,type,item[key]);f.querySelector('input').removeAttribute('id');row.append(f);
 }
 const remove=document.createElement('button');remove.type='button';remove.className='remove';remove.textContent='×';remove.setAttribute('aria-label','Remove item');remove.onclick=()=>{if ($('#items').children.length > 1) {row.remove();changed();}};row.append(remove);$('#items').append(row);
}
function collect(){
 const d={};if (logo) d.logo=logo;for(const [,fields] of groups)for(const [k] of fields)d[k]=$('#'+k).value || (k === 'tax_rate' ? '0' : '');
 d.items=[...document.querySelectorAll('.item')].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(i=>[i.name,i.value || (i.name === 'discount' ? '0' : '')])));return d;
}
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const result=await r.json();if(!r.ok)throw Error(result.error||'Could not load receipt.');return result;}
function status(message,error=false){$('#status').textContent=message;$('#status').classList.toggle('error',error);}
function displayReceipt(html, width) {
 $('#preview').innerHTML=html;
 $('#paper-label').textContent=width+' mm';
}
async function preview(){
 const current=++revision;
 try {
  const d=collect(), result=await api('/api/preview',d);
  if(current!==revision)return false;
  displayReceipt(result.html,d.width);
  if (!dirty || lastAutosave) status(dirty ? 'Draft autosaved in this browser.' : 'Preview up to date');
  return true;
 } catch(error) {
  if(current===revision)status(error.message,true);
  return false;
 }
}
let lastAutosave = true;
function changed(){
 dirty=true;
 issueToken='';
 lastAutosave=writeLocal(draftKey,{receipt:collect(), token:issueToken});
 if (!lastAutosave) status('Draft could not be autosaved. Keep this tab open.',true);
 schedule();
}
function schedule(){++revision;clearTimeout(timer);timer=setTimeout(preview,200);}
async function saved({query = historyQuery, append = false} = {}) {
 const params = new URLSearchParams({q: query});
 if (append) params.set('before', nextBefore);
 const result = await api('/api/receipts/history?' + params);
 const select = $('#saved');
 if (!append) select.replaceChildren(new Option('Choose a receipt…', ''));
 for (const receipt of result.receipts) {
  if (receipt.issued) issuedIds.add(String(receipt.id));
  select.add(new Option(`${receipt.number || 'Untitled'}${receipt.issued ? ' · Issued' : ''} · ${receipt.created} UTC · #${receipt.id}`, receipt.id));
 }
 historyQuery = query;
 nextBefore = result.next_before;
 select.value = [...select.options].some(option => option.value === savedId) ? savedId : '';
 const count = select.options.length - 1;
 $('#history-status').textContent = count ? `${count} receipts shown` : 'No matching receipts.';
}
$('#form').addEventListener('input',changed);$('#form').addEventListener('submit',e=>e.preventDefault());
async function action(work) {
 if (busy) return;
 busy = true;
 const controls = ['#save', '#print', '#new', '#saved', '#receipt-search', '#search-receipts', '#more-receipts'].map($);
 controls.forEach(control => { control.disabled = true; });
 $('#fields').inert = true;
 try { await work(); }
 catch (error) { status(error.message, true); }
 finally {
  $('#fields').inert = false;
  controls.forEach(control => { control.disabled = false; });
  syncMode();
  $('#more-receipts').disabled = nextBefore === null;
  busy = false;
 }
}

function syncMode() {
 const issued = Boolean(issuedHtml);
 $('#fields').inert = issued;
 $('#save').disabled = issued;
 $('#duplicate').hidden = !issued;
 $('#print').textContent = issued ? 'Reprint / Save PDF' : 'Print / Save PDF';
 for (const id of ['#apply-profile','#save-profile','#logo-file','#remove-logo']) $(id).disabled = issued;
}
$('#save').onclick = () => action(async () => {
 const receipt=collect();
 const amountPreview=await api('/api/preview',receipt);
 if (amountPreview.unbalanced && !confirm('Payments entered differ from the receipt total. Issue anyway?')) return;
 issueToken ||= crypto.randomUUID();
 writeLocal(draftKey,{receipt, token:issueToken});
 const result=await api('/api/issue',{request_id:issueToken,receipt});
 currentReceipt={...receipt,number:result.number};
 issuedHtml=result.html;
 dirty=false;
 issueToken='';
 writeLocal(draftKey,null);
 clearTimeout(timer);
 ++revision;
 displayReceipt(issuedHtml,receipt.width);
 if ($('#number')) $('#number').value=result.number;
 savedId=String(result.id);
 issuedIds.add(savedId);
 status('Issued '+result.number);
 try {await saved({query:''});$('#receipt-search').value='';}
 catch {status('Receipt issued, but the history list could not be refreshed.',true);}
});
$('#print').onclick = () => action(async () => {
 clearTimeout(timer);
 if (!issuedHtml && !await preview()) return;
 await Promise.all([...$('#preview').querySelectorAll('img')].map(image => image.decode()));
 window.print();
});
async function openReceipt(id) {
 const receipt=await api(id ? '/api/receipts/' + id : '/api/default');
 const original=issuedIds.has(id) ? await api('/api/issued/'+id) : null;
 issuedHtml=original?.html || '';
 issueToken='';
 build(receipt);
 if (issuedHtml) {
  clearTimeout(timer);
  displayReceipt(issuedHtml,receipt.width);
  status('Issued '+receipt.number);
 }
 savedId=id;
 $('#saved').value=id;
}
$('#new').onclick = () => {
 if (!busy && discard()) return action(async () => {await openReceipt('');writeLocal(draftKey,null);});
};
$('#duplicate').onclick = () => action(() => {
 const copy={...currentReceipt,number:'',invoice:'',verification:'',fdn:'',qr:''};
 issuedHtml='';
 savedId='';
 $('#saved').value='';
 build(copy);
 changed();
});
$('#saved').onchange = event => {
 const id=event.target.value;
 event.target.value=[...event.target.options].some(option => option.value===savedId) ? savedId : '';
 if (!busy && id && discard()) return action(async () => {await openReceipt(id);writeLocal(draftKey,null);});
};
function loadProfiles() {
 const profiles=readLocal(profileKey) || [];
 $('#profiles').replaceChildren(new Option('Choose profile…',''));
 for (const profile of profiles) $('#profiles').add(new Option(profile.name,profile.name));
 return profiles;
}
$('#save-profile').onclick=() => {
 if (busy || issuedHtml) return;
 const name=$('#profile-name').value.trim();
 if (!name) return status('Enter a profile name.',true);
 const profiles=loadProfiles().filter(profile=>profile.name!==name);
 const receipt=collect();
 const values=Object.fromEntries(profileFields.map(key=>[key,receipt[key] || '']));
 profiles.push({name,values});
 if (!writeLocal(profileKey,profiles)) return status('Profile could not be saved in this browser.',true);
 loadProfiles();
 $('#profiles').value=name;
 status('Profile saved in this browser.');
};
$('#apply-profile').onclick=() => {
 if (busy || issuedHtml) return;
 const name=$('#profiles').value;
 const profile=(readLocal(profileKey) || []).find(entry=>entry.name===name);
 if (!profile) return status('Choose a saved profile.',true);
 build({...collect(),...profile.values});
 changed();
};
$('#logo-file').onchange=event => {
 const file=event.target.files[0];
 if (!file || busy || issuedHtml) return;
 if (!['image/png','image/jpeg'].includes(file.type) || file.size>100000) return status('Choose a PNG or JPEG up to 100 KB.',true);
 return action(async () => {
  logo=await new Promise((resolve,reject)=>{
   const reader=new FileReader();
   reader.onload=()=>resolve(reader.result);
   reader.onerror=()=>reject(Error('Could not read the selected logo.'));
   reader.readAsDataURL(file);
  });
  changed();
 });
};
$('#remove-logo').onclick=() => {if (!busy && !issuedHtml) {logo='';$('#logo-file').value='';changed();}};
$('#history-search').onsubmit = event => {
 event.preventDefault();
 const query = $('#receipt-search').value.trim();
 return action(() => saved({query}));
};
$('#more-receipts').onclick = () => {
 if (nextBefore !== null) return action(() => saved({append: true}));
};
action(async () => {
 loadProfiles();
 const draft=readLocal(draftKey);
 if (draft?.receipt?.items?.length) {
  build(draft.receipt);
  issueToken=draft.token || '';
  dirty=true;
 } else await openReceipt('');
 await saved();
});
