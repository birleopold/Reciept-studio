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
let data, timer, revision = 0;
function field(key,label,type='text',value='') {
 const wrap=document.createElement('label'); wrap.textContent=label;
 const input=document.createElement(type==='textarea'?'textarea':type==='select'?'select':'input');
 input.name=key; input.id=key;
 if(type==='select') {for(const w of ['80','58']) {const o=new Option(w+' mm',w);input.add(o);}}
 else if(type!=='textarea') {input.type=type; if(type==='number'){input.min='0';input.step='any';}}
 input.value=value; wrap.append(input); return wrap;
}
function build(d) {
 data=d; $('#fields').replaceChildren();
 for(const [title,fields] of groups){
  const section=document.createElement('details'); section.open=['Delivery header','Items'].includes(title);
  const summary=document.createElement('summary');summary.textContent=title;section.append(summary);
  const grid=document.createElement('div');grid.className='field-grid';
  for(const [key,label,type] of fields) grid.append(field(key,label,type,d[key]));
  if(title==='Items'){
   grid.className='items';grid.id='items';section.append(grid);
   const add=document.createElement('button');add.type='button';add.className='add-item';add.textContent='+ Add item';add.onclick=()=>{addItem({name:'New item',qty:'1',price:'0'});schedule();};section.append(add);
  } else section.append(grid);
  if(title==='QR code & footer'){const note=document.createElement('p');note.className='hint';note.textContent='Enter your own QR content. Leave empty to hide it. Verification code and FDN are supplied by your invoicing system; this app does not issue them.';section.append(note);}
  $('#fields').append(section);
 }
 d.items.forEach(addItem);schedule();
}
function addItem(item){
 const row=document.createElement('div');row.className='item';
 for(const [key,label,type] of [['name','Item name','text'],['qty','Qty','number'],['price','Unit price','number']]){
  const f=field(key,label,type,item[key]);f.querySelector('input').removeAttribute('id');row.append(f);
 }
 const remove=document.createElement('button');remove.type='button';remove.className='remove';remove.textContent='×';remove.setAttribute('aria-label','Remove item');remove.onclick=()=>{row.remove();schedule();};row.append(remove);$('#items').append(row);
}
function collect(){
 const d={};for(const [,fields] of groups)for(const [k] of fields)d[k]=$('#'+k).value;
 d.items=[...document.querySelectorAll('.item')].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(i=>[i.name,i.value])));return d;
}
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const result=await r.json();if(!r.ok)throw Error(result.error||'Could not load receipt.');return result;}
function status(message,error=false){$('#status').textContent=message;$('#status').classList.toggle('error',error);}
async function preview(){const current=++revision;try{const d=collect(),r=await api('/api/preview',d);if(current!==revision)return false;$('#preview').innerHTML=r.html;$('#paper-label').textContent=d.width+' mm';let style=$('#print-size');if(!style){style=document.createElement('style');style.id='print-size';document.head.append(style);}style.textContent=`@media print {@page {size: ${d.width}mm auto; margin: 0;} html,body {width:${d.width}mm;}}`;status('Preview up to date');return true;}catch(e){if(current===revision)status(e.message,true);return false;}}
function schedule(){++revision;clearTimeout(timer);timer=setTimeout(preview,200);}
async function saved(){const rows=await api('/api/receipts');$('#saved').replaceChildren(new Option('Choose a receipt…',''));for(const r of rows)$('#saved').add(new Option(`${r.number||'Untitled'} · ${r.created} UTC · #${r.id}`,r.id));}
$('#form').addEventListener('input',schedule);$('#form').addEventListener('submit',e=>e.preventDefault());
$('#save').onclick=async()=>{try{const r=await api('/api/receipts',collect());await saved();$('#saved').value=r.id;status('Receipt saved on this computer.');}catch(e){status(e.message,true);}};
$('#print').onclick=async()=>{clearTimeout(timer);if(await preview()){await Promise.all([...$('#preview').querySelectorAll('img')].map(i=>i.decode()));window.print();}};
$('#new').onclick=async()=>{if(!confirm('Start a new receipt? Save your current receipt first if you want to keep it.'))return;try{build(await api('/api/default'));$('#saved').value='';}catch(e){status(e.message,true);}};
$('#saved').onchange=async e=>{if(e.target.value)try{build(await api('/api/receipts/'+e.target.value));}catch(err){status(err.message,true);}};
(async()=>{try{build(await api('/api/default'));await saved();}catch(e){status(e.message,true);}})();
