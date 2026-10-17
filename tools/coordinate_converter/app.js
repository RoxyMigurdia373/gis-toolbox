/* Coordinate conversion core. All calculations stay in the browser. */
function parseCoordinate(text, mode, limit) {
  const clean = text.trim().replace(/[°º度′’‘'分″“”"秒]/g,' ').replace(/\s+/g,' ').trim();
  const parts = clean.split(' ');
  const count = {dd:1,dm:2,dms:3}[mode];
  if(parts.length!==count || !/^[+-]?\d+(?:\.\d*)?$/.test(parts[0]) || parts.slice(1).some(p=>!/^\d+(?:\.\d*)?$/.test(p))) throw Error('格式不符，请按所选格式输入');
  const values=parts.map(Number), d=Math.abs(values[0]), m=values[1]||0, s=values[2]||0;
  if(mode!=='dd' && !Number.isInteger(d)) throw Error('度必须是整数，小数请填在最后一项');
  if(mode==='dms' && !Number.isInteger(m)) throw Error('度分秒格式的分必须是整数');
  if(m>=60 || s>=60) throw Error('分、秒必须小于 60');
  const value=d+m/60+s/3600;
  if(!Number.isFinite(value)||d>limit||value>limit||(d===limit&&(m!==0||s!==0))) throw Error('坐标超出范围：经度 ±180°，纬度 ±90°');
  return parts[0].startsWith('-') ? -value : value;
}
function formatCoordinate(value,mode,p) {
  const scale=10**p, magnitude=Math.abs(value);
  if(mode==='dd') { const str=value.toFixed(p); return Number(str)===0 ? (0).toFixed(p):str; }
  // Round the total units first so 60 seconds/minutes carry into the next unit.
  const units=mode==='dm'?60:3600;
  let ticks=Math.round(magnitude*units*scale);
  const sign=value<0 && ticks!==0?'-':'';
  const d=Math.floor(ticks/(units*scale)); ticks-=d*units*scale;
  if(mode==='dm') return sign+d+'°'+(ticks/scale).toFixed(p)+'′';
  const m=Math.floor(ticks/(60*scale));ticks-=m*60*scale;
  return sign+d+'°'+m+'′'+(ticks/scale).toFixed(p)+'″';
}
function projectionZones(lon,lat){
  let utm=Math.min(60,Math.floor((lon+180)/6)+1);
  if(lat>=56&&lat<64&&lon>=3&&lon<12)utm=32;
  if(lat>=72&&lat<=84&&lon>=0&&lon<42)utm=lon<9?31:lon<21?33:lon<33?35:37;
  const hemisphere=lat<0?'S':'N';
  const gk=Math.floor((lon+1.5)/3),cm=gk*3;
  return {utm,hemisphere,utmEpsg:(lat<0?32700:32600)+utm,utmValid:lat>=-80&&lat<=84,gk,cm,gkValid:gk>=25&&gk<=45&&lat>=0,gkCmEpsg:4534+gk-25,gkZoneEpsg:4513+gk-25};
}
function showZones(lon,lat){
  const z=projectionZones(lon,lat);
  const utm=z.utmValid?'<strong>UTM '+z.utm+z.hemisphere+'</strong> · '+(z.hemisphere==='N'?'北半球':'南半球')+'<br>WGS 84 / UTM zone '+z.utm+z.hemisphere+'<br>EPSG:'+z.utmEpsg:'此纬度超出 UTM 常规适用范围（80°S—84°N）';
  const gk=z.gkValid?'<strong>3° GK 第 '+z.gk+' 带 · 中央经线 '+z.cm+'°E</strong><br>CGCS2000 / 3-degree Gauss-Kruger CM '+z.cm+'E<br>EPSG:'+z.gkCmEpsg+'（CM，无带号前缀）<br><small>带号前缀版本：zone '+z.gk+' · EPSG:'+z.gkZoneEpsg+'</small>':'此位置不提供中国 CGCS2000 标准 3° GK 分带推荐';
  $('#zones').innerHTML='<p>WGS 84（84）<br>'+utm+'</p><p>CGCS2000（2000）<br>'+gk+'</p>';
}
const $=s=>document.querySelector(s), names=['经度','纬度'],limits=[180,90], labels={dd:'十进制度',dm:'度分（小数分）',dms:'度分秒'};
let active=0, fields=[], lastValues=null;
let mode='dms';
function message(text,error=false){$('#status').textContent=text;$('#status').classList.toggle('error',error)}
function invalidate(text,error=false){$('#zones').textContent='输入完整有效经纬度后显示';lastValues=null;$('#result').value='';$('#copy').disabled=true;$('#copy').textContent='复制坐标';message(text,error)}
function render(values=null){
  const units=mode==='dd'?['度']:mode==='dm'?['度','分']:['度','分','秒'];
  $('#coordinates').innerHTML=names.map((name,axis)=>'<section class="coordinate" aria-label="'+name+'"><div class="label">'+name+'<select class="direction" aria-label="'+name+'方向"><option value="1">'+(axis===0?'东经 E':'北纬 N')+'</option><option value="-1">'+(axis===0?'西经 W':'南纬 S')+'</option></select></div><input class="paste-input" data-axis="'+axis+'" aria-label="粘贴'+name+'或整组坐标" placeholder="'+(mode==='dd'?'粘贴十进制度，如 107.887611':mode==='dm'?'粘贴度分，如 107°53.256667′':'粘贴度分秒，如 107°53′15.40″')+'"><div class="fields '+(units.length===1?'single':units.length===2?'double':'')+'">'+units.map((u,i)=>'<label class="field"><input aria-label="'+name+' '+u+'" data-axis="'+axis+'" data-unit="'+i+'" readonly inputmode="none" placeholder="'+u+'"><span>'+['°','′','″'][i]+'</span></label>').join('')+'</div></section>').join('');
  fields=[...document.querySelectorAll('.field input')]; active=0;
  fields.forEach((f,i)=>{f.addEventListener('focus',()=>active=i);f.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return; if(/^[0-9.]$/.test(e.key)){e.preventDefault();key(e.key)}else if(e.key==='Backspace'||e.key==='Delete'){e.preventDefault();key(e.key==='Delete'?'clear-field':'backspace')}else if(e.key==='Enter'){e.preventDefault();key('next')}else if(e.key==='-'){e.preventDefault();key('sign')}});f.addEventListener('paste',e=>{e.preventDefault();const t=e.clipboardData.getData('text').trim();if(/^\d+(?:\.\d*)?$/.test(t)){f.value=t;update()}else paste(t,Number(f.dataset.axis))})});
  document.querySelectorAll('.paste-input').forEach(input=>input.addEventListener('input',()=>paste(input.value,Number(input.dataset.axis))));
  document.querySelectorAll('.direction').forEach(s=>s.addEventListener('change',update));
  if(values) values.forEach((v,a)=>put(v,a));
  update();
}
function put(value,axis){
  const text=formatCoordinate(Math.abs(value),mode,10).replace(/[°′″]/g,' ').trim().split(' ');
  fields.filter(f=>Number(f.dataset.axis)===axis).forEach((f,i)=>f.value=String(Number(text[i])));
  document.querySelectorAll('.direction')[axis].value=value<0||Object.is(value,-0)?'-1':'1';
}
function current(){
  return names.map((_,axis)=>{
    const group=fields.filter(f=>Number(f.dataset.axis)===axis);
    if(group.some(f=>!f.value))return null;
    return parseCoordinate(group.map(f=>f.value).join(' '),mode,limits[axis])*Number(document.querySelectorAll('.direction')[axis].value);
  });
}
function update(){
  fields.forEach(f=>f.style.fontSize=f.value.length>10?'15px':f.value.length>8?'18px':'21px');
  $('#result-label').textContent=labels[$('#to').value];$('#copy').textContent='复制坐标';
  try{const values=current(); if(values.includes(null)){invalidate('输入或粘贴坐标，自动转换');return}lastValues=values;showZones(values[0],values[1]);$('#result').value=values.map(v=>formatCoordinate(v,$('#to').value,Number($('#precision').value))).join(',');$('#copy').disabled=false;message('已转换 · 经度在前，纬度在后')}catch(e){invalidate(e.message,true)}
}
function paste(text,axis){
  if(!text.trim()){fields.filter(f=>Number(f.dataset.axis)===axis).forEach(f=>f.value='');update();return}
  try{const parts=text.trim().split(/[,，;；\r\n]+/).filter(t=>t.trim());if(parts.length<1||parts.length>2)throw Error('整组坐标请按经度、纬度顺序，用逗号分隔');const parsed=parts.map((t,i)=>parseCoordinate(t,mode,limits[parts.length===2?i:axis]));parsed.forEach((v,i)=>put(v,parts.length===2?i:axis));update()}catch(e){fields.filter(f=>Number(f.dataset.axis)===axis).forEach(f=>f.value='');invalidate(e.message,true)}
}
function key(k){
  const f=fields[active], group=fields.filter(x=>x.dataset.axis===f.dataset.axis);
  if(k==='next')active=(active+1)%fields.length;
  else if(k==='clear'){fields.forEach(x=>x.value='');document.querySelectorAll('.paste-input').forEach(x=>x.value='');active=0}
  else if(k==='sign'){const s=document.querySelectorAll('.direction')[Number(f.dataset.axis)];s.value=s.value==='1'?'-1':'1'}
  else if(k==='clear-field')f.value='';
  else if(k==='backspace')f.value=f.value.slice(0,-1);
  else if(k==='.'){if(f!==group[group.length-1]){message('只有最后一项可以输入小数',true);return}if(!f.value.includes('.'))f.value=(f.value||'0')+'.'}
  else if(/^\d$/.test(k)&&f.value.length<16)f.value+=k;
  fields[active].focus({preventScroll:true});update();
}
document.querySelectorAll('[data-key]').forEach(b=>{b.addEventListener('mousedown',e=>e.preventDefault());b.addEventListener('click',()=>key(b.dataset.key))});
$('#from').addEventListener('change',()=>{const values=lastValues; mode=$('#from').value;render(values)});
$('#to').addEventListener('change',()=>{ $('#precision').value=$('#to').value==='dms'?'2':$('#to').value==='dm'?'5':'6';update()});
$('#precision').addEventListener('change',update);
$('#swap').addEventListener('click',()=>{const values=lastValues,old=mode;mode=$('#to').value;$('#from').value=mode;$('#to').value=old;$('#precision').value=old==='dms'?'2':'6';render(values)});
$('#result').addEventListener('click',()=>$('#result').select());
$('#copy').addEventListener('click',async()=>{if(!$('#result').value)return;try{if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText($('#result').value);else{$('#result').select();if(!document.execCommand('copy'))throw Error()}$('#copy').textContent='已复制 ✓';message('坐标已复制')}catch{$('#result').focus();$('#result').select();message('请长按结果或按 Ctrl+C 复制')}});
render();
