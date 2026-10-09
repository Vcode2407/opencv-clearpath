const $ = id => document.getElementById(id);
let fixtures = [], inputMode = 'demo', corners = [], uploadedImage = null, latestReport = null;
const apiHeaders = () => $('cloud-token').value ? {Authorization: `Bearer ${$('cloud-token').value}`} : {};
function error(message) { $('input-error').textContent = message; $('input-error').hidden = !message; }
async function responseJSON(response) {
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'The inspection could not finish.');
  return body;
}
function fixturePreview() {
  const selected = fixtures.find(item => item.id === $('fixture').value);
  if (!selected) return;
  $('fixture-preview').src = `/fixtures/${selected.image}`;
  $('fixture-note').textContent = selected.known_limitation ? 'Known failure case: this object is too close in colour to the floor. Review the missed region.' : 'Owned synthetic scene · 2.4 m × 6.0 m floor · independently labelled dimensions.';
}
async function loadFixtures() {
  const data = await responseJSON(await fetch('/api/fixtures', {headers: apiHeaders()}));
  fixtures = data.fixtures;
  $('fixture').replaceChildren(...fixtures.map(item => new Option(item.title, item.id)));
  $('fixture').value = 'pinch'; fixturePreview(); error('');
}
function mode(next) {
  inputMode = next; error('');
  $('demo-panel').hidden = next !== 'demo'; $('upload-panel').hidden = next !== 'upload';
  ['demo', 'upload'].forEach(item => { $(`${item}-tab`).classList.toggle('active', item === next); $(`${item}-tab`).setAttribute('aria-selected', String(item === next)); });
}
function drawCorners() {
  if (!uploadedImage) return;
  const canvas = $('calibration-canvas'), ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.drawImage(uploadedImage, 0, 0, canvas.width, canvas.height);
  const scale = canvas.width / uploadedImage.naturalWidth;
  ctx.strokeStyle = '#c3e889'; ctx.lineWidth = 3;
  if (corners.length) {
    ctx.beginPath(); corners.forEach(([x,y], i) => i ? ctx.lineTo(x*scale,y*scale) : ctx.moveTo(x*scale,y*scale));
    if (corners.length === 4) ctx.closePath(); ctx.stroke();
  }
  corners.forEach(([x,y],i) => {ctx.fillStyle='#145749';ctx.beginPath();ctx.arc(x*scale,y*scale,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='white';ctx.font='bold 12px sans-serif';ctx.fillText(String(i+1),x*scale-3,y*scale+4);});
  $('corner-count').textContent = `${corners.length} of 4 corners`;
}
$('scene').addEventListener('change', () => {
  const file = $('scene').files[0]; corners = []; uploadedImage = null; $('calibration-picker').hidden = true;
  if (!file) return;
  if (file.size > 8_000_000) return error('Resize the image to below 8 MB first.');
  const source = URL.createObjectURL(file), image = new Image();
  image.onload = () => {URL.revokeObjectURL(source); if(image.naturalWidth*image.naturalHeight>8_000_000)return error('Resize the image to at most 8 megapixels.');uploadedImage=image;const canvas=$('calibration-canvas');canvas.width=Math.min(900,image.naturalWidth);canvas.height=Math.round(image.naturalHeight*canvas.width/image.naturalWidth);$('calibration-picker').hidden=false;drawCorners();error('');};
  image.onerror = () => {URL.revokeObjectURL(source);error('Could not read this image. Use a PNG or JPEG.');}; image.src=source;
});
$('calibration-canvas').addEventListener('click', event => {
  if (!uploadedImage || corners.length >= 4) return;
  const box = event.currentTarget.getBoundingClientRect();
  corners.push([(event.clientX-box.left)/box.width*uploadedImage.naturalWidth,(event.clientY-box.top)/box.height*uploadedImage.naturalHeight]);drawCorners();
});
$('reset-corners').addEventListener('click',()=>{corners=[];drawCorners();});
$('demo-tab').addEventListener('click',()=>mode('demo'));
$('upload-tab').addEventListener('click',()=>mode('upload'));
$('fixture').addEventListener('change',fixturePreview);
$('unlock').addEventListener('click',()=>loadFixtures().catch(err=>error(err.message)));
function listInto(id, values) {$(id).replaceChildren(...values.map(value=>{const li=document.createElement('li');li.textContent=value;return li;}));}
function showReport(report) {
  latestReport = report; const retry = report.status === 'needs_capture', measurement=report.measurements;
  $('empty-result').hidden=true;$('result').hidden=false;$('reviewed').checked=false;
  $('review-state').textContent='Your review is recorded only in this browser view.';
  $('status-card').classList.toggle('retry',retry);$('status-label').textContent=retry?'CAPTURE CHECK / RETRY':'MEASUREMENT / HUMAN REVIEW REQUIRED';
  $('status-title').textContent=retry?'A better view is needed':measurement.below_review_target?'The measured span is below your target':'Measurements are ready to review';
  $('status-card').setAttribute('aria-label', `${report.source || 'Inspection'}: ${$('status-title').textContent}`);
  $('status-icon').textContent=retry?'↻':'↗';$('capture-request').hidden=!retry;listInto('capture-list',report.capture_requests);
  $('metrics').hidden=retry;$('rectified-figure').hidden=!report.rectified_image;
  $('annotated').src=report.annotated_image;if(report.rectified_image)$('rectified').src=report.rectified_image;
  if(measurement){$('clearance').textContent=`${measurement.clearance_m.toFixed(2)} m`;$('area').textContent=`${measurement.changed_area_m2.toFixed(2)} m²`;$('regions').textContent=`${measurement.obstacle_count} detected changed regions`;$('target-result').textContent=`Review target ${measurement.review_width_m.toFixed(2)} m · ${measurement.below_review_target?'below target':'at or above target'}`;}
  $('review-description').textContent=retry?'Follow the capture requests and inspect the new aligned image pair before using any measurements.':'The span is the smallest widest free cross-section on the calibrated floor. A green line marks that section. Red regions show changes from the empty reference; low-contrast objects may be missed. This does not establish a continuous body-width route.';
  listInto('trace',report.trace.map(step=>`${step.step.replaceAll('_',' ')} — ${step.outcome}`));
  $('quality').textContent=JSON.stringify(report.quality,null,2);listInto('limitations',report.limitations);
  $('download-image').href=report.annotated_image;
}
$('inspect').addEventListener('click',async()=>{
  error('');const button=$('inspect');button.disabled=true;button.firstChild.textContent='Inspecting… ';
  try {
    const target=Number($('target').value);if(!Number.isFinite(target)||target<0.2||target>5)throw new Error('Choose a review target between 0.2 and 5 metres.');
    let options;
    if(inputMode==='demo'){options={method:'POST',headers:{...apiHeaders(),'Content-Type':'application/json'},body:JSON.stringify({fixture:$('fixture').value,review_width_m:target})};}
    else{if(!$('scene').files[0]||!$('reference').files[0])throw new Error('Upload both the current scene and an aligned empty reference.');if(corners.length!==4)throw new Error('Select all four measured floor corners on the scene.');const form=new FormData();form.append('scene',$('scene').files[0]);form.append('reference',$('reference').files[0]);form.append('calibration',JSON.stringify({points:corners,width_m:Number($('width').value),length_m:Number($('length').value),review_width_m:target}));options={method:'POST',headers:apiHeaders(),body:form};}
    showReport(await responseJSON(await fetch('/api/inspect',options)));
  } catch(err) {error(err.message);} finally {button.disabled=false;button.firstChild.textContent='Inspect this view ';}
});
$('reviewed').addEventListener('change',()=>{$('review-state').textContent=$('reviewed').checked?'Overlay review acknowledged in this browser view. This is not a safety certification.':'Your review is recorded only in this browser view.';});
$('download-json').addEventListener('click',()=>{if(!latestReport)return;const payload={...latestReport,human_review_acknowledged:$('reviewed').checked};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='clearpath-report.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
(async()=>{try{const health=await responseJSON(await fetch('/health'));const location=health.mode==='aws'?(health.aws_deployment_verified===true?'AWS deployment verified':'cloud mode · deployment unverified'):'local';$('runtime').textContent=`OpenCV ${health.opencv_version} · CPU · ${location}`;if(health.mode==='aws')$('cloud-token-row').hidden=false;else await loadFixtures();}catch(err){$('runtime').textContent='Runtime unavailable';error(err.message);}})();
