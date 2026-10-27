
const cache=new Map();
const observed=new WeakSet();
async function artwork(id){
 if(!cache.has(id))cache.set(id,(async()=>{
  const fields='id,title,date_display,medium_display,artist_display,image_id,is_public_domain,main_reference_number,dimensions,thumbnail';
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),20000);
  let r;try{r=await fetch('https://api.artic.edu/api/v1/artworks/'+id+'?fields='+fields,{signal:controller.signal});}finally{clearTimeout(timer);}
  if(!r.ok)throw new Error('museum API '+r.status);
  const j=await r.json();if(!j.data?.image_id)throw new Error('image unavailable');
  const root=(j.config?.iiif_url||'https://www.artic.edu/iiif/2')+'/'+j.data.image_id;
  return {data:j.data,root};
 })().catch(err=>{cache.delete(id);throw err;}));return cache.get(id);
}
async function loadFigure(fig){
 if(observed.has(fig))return;observed.add(fig);
 const status=fig.querySelector('.status'),im=fig.querySelector('img');
 try{
  const {data:d,root}=await artwork(fig.dataset.id);
  const full=root+'/full/full/0/default.jpg';
  const jpg=fig.querySelector('.jpg');jpg.href=full;jpg.hidden=false;
  fig.querySelector('.image-frame').href=full;
  const text=[d.date_display,d.medium_display,d.dimensions].filter(Boolean).join(' · ');
  fig.querySelector('.museum-meta').textContent='Музейная запись: '+text;
  im.onload=()=>{im.hidden=false;status.hidden=true;};
  im.onerror=()=>{status.textContent='Скан не загрузился. Откройте музейную карточку или JPG по ссылке ниже.';};
  im.src=root+'/full/!1400,1400/0/default.jpg';
 }catch(err){observed.delete(fig);status.textContent='Музейный сервис недоступен. Проверьте интернет или откройте карточку по ссылке ниже.';}
}
const obs=new IntersectionObserver(entries=>entries.forEach(en=>{if(en.isIntersecting){loadFigure(en.target);obs.unobserve(en.target);}}),{rootMargin:'600px'});
document.querySelectorAll('.work').forEach(f=>obs.observe(f));
document.getElementById('load-all').addEventListener('click',async function(){
 this.textContent='Загрузка музейных репродукций…';
 const figs=[...document.querySelectorAll('#all-images .work')];
 for(let i=0;i<figs.length;i+=3)await Promise.allSettled(figs.slice(i,i+3).map(loadFigure));
 this.textContent='Запросы выполнены — сохраните нужные JPG по ссылкам';
});
