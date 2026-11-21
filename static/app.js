const $ = s => document.querySelector(s);
const groups = [
 ['Delivery header', [['headline','Heading'],['phone_label','Phone label'],['phone1','First phone'],['phone2','Second phone']]],
 ['Business details', [['business','Business / branch'],['address','Address'],['tin','Business TIN'],['title','Receipt title']]],
 ['Invoice details', [['customer','Customer TIN / name'],['date','Date','date'],['number','Receipt number'],['invoice','Invoice number'],['verification','Verification code'],['fdn','FDN']]],
 ['Items', []],
 ['Payment breakdown', [['cash','Cash','number'],['card','Credit card','number'],['coupon','Coupon','number'],['mobile','Mobile money','number'],['loyalty','Loyalty','number'],['gift','Gift card','number'],['promo','Promo','number'],['vat','VAT note']]],
 ['Delivery details', [['delivery_title','Section heading'],['recipient','Recipient name'],['area','Delivery address','textarea'],['delivery_phone','Delivery phone']]],
 ['QR code & footer', [['qr','QR code content / verification URL','textarea'],['airtel','Airtel instructions'],['momo','MoMo instructions'],['width','Paper width','select']]]
];
let timer, revision = 0, dirty = false, savedId = '', busy = false;
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
 input.value=value; wrap.append(input); return wrap;
}
function build(d) {
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
 for(const [key,label,type] of [['name','Item name','text'],['qty','Qty','number'],['price','Unit price','number']]){
  const f=field(key,label,type,item[key]);f.querySelector('input').removeAttribute('id');row.append(f);
 }
 const remove=document.createElement('button');remove.type='button';remove.className='remove';remove.textContent='×';remove.setAttribute('aria-label','Remove item');remove.onclick=()=>{if ($('#items').children.length > 1) {row.remove();changed();}};row.append(remove);$('#items').append(row);
}
function collect(){
 const d={};for(const [,fields] of groups)for(const [k] of fields)d[k]=$('#'+k).value;
 d.items=[...document.querySelectorAll('.item')].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(i=>[i.name,i.value])));return d;
}
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const result=await r.json();if(!r.ok)throw Error(result.error||'Could not load receipt.');return result;}
function status(message,error=false){$('#status').textContent=message;$('#status').classList.toggle('error',error);}
async function preview(){const current=++revision;try{const d=collect(),r=await api('/api/preview',d);if(current!==revision)return false;$('#preview').innerHTML=r.html;$('#paper-label').textContent=d.width+' mm';let style=$('#print-size');if(!style){style=document.createElement('style');style.id='print-size';document.head.append(style);}style.textContent=`@media print {@page {size: ${d.width}mm auto; margin: 0;} html,body {width:${d.width}mm;}}`;status('Preview up to date');return true;}catch(e){if(current===revision)status(e.message,true);return false;}}
function changed(){dirty=true;schedule();}
function schedule(){++revision;clearTimeout(timer);timer=setTimeout(preview,200);}
async function saved(){const rows=await api('/api/receipts');$('#saved').replaceChildren(new Option('Choose a receipt…',''));for(const r of rows)$('#saved').add(new Option(`${r.number||'Untitled'} · ${r.created} UTC · #${r.id}`,r.id));}
$('#form').addEventListener('input',changed);$('#form').addEventListener('submit',e=>e.preventDefault());
async function action(work) {
 if (busy) return;
 busy = true;
 const controls = ['#save', '#print', '#new', '#saved'].map($);
 controls.forEach(control => { control.disabled = true; });
 $('#fields').inert = true;
 clearTimeout(timer);
 ++revision;
 try { await work(); }
 catch (error) { status(error.message, true); }
 finally {
  $('#fields').inert = false;
  controls.forEach(control => { control.disabled = false; });
  busy = false;
 }
}

$('#save').onclick = () => action(async () => {
 const result = await api('/api/receipts', collect());
 dirty = false;
 $('#preview').innerHTML = result.html;
 savedId = String(result.id);
 status('Receipt saved on this computer.');
 try { await saved(); $('#saved').value = savedId; }
 catch { status('Receipt saved, but the saved list could not be refreshed.', true); }
});
$('#print').onclick = () => action(async () => {
 if (!await preview()) return;
 await Promise.all([...$('#preview').querySelectorAll('img')].map(image => image.decode()));
 window.print();
});
async function openReceipt(id) {
 build(await api(id ? '/api/receipts/' + id : '/api/default'));
 savedId = id;
 $('#saved').value = id;
}
$('#new').onclick = () => { if (!busy && discard()) return action(() => openReceipt('')); };
$('#saved').onchange = event => {
 const id = event.target.value;
 event.target.value = savedId;
 if (!busy && id && discard()) return action(() => openReceipt(id));
};
action(async () => { await openReceipt(''); await saved(); });
