# Plantillas HTML/JS/CSS para cada genero de juego. Uso interno de juegos_movil.

def get_shooter_html(titulo):
    return _BASE.format(
        titulo=titulo,
        estilos=_STYLE_SHOOTER,
        body="""
<div id="c">
<div id="puntos">0</div>
<div id="vidas">3</div>
<div id="nave"></div>
<div id="btn"><button>JUGAR</button></div>
</div>
<div id="controles" style="display:none;"><button id="izq">&#9664;</button><button id="disparo">DISPARO</button><button id="der">&#9654;</button></div>
""",
        script=_SCRIPT_SHOOTER,
    )

def get_snake_html(titulo):
    return _BASE.format(
        titulo=titulo,
        estilos=_STYLE_SNAKE,
        body="""
<div id="c"><canvas id="can"></canvas><div id="puntos">0</div><div id="btn"><button>JUGAR</button></div></div>
<div id="controles" style="display:none;"><button id="izq">&#9664;</button><button id="arriba">&#9650;</button><button id="der">&#9654;</button><button id="abajo">&#9660;</button></div>
""",
        script=_SCRIPT_SNAKE,
    )

def get_memoria_html(titulo):
    return _BASE.format(
        titulo=titulo,
        estilos=_STYLE_MEMORIA,
        body='<div id="c"><div id="tablero"></div><div id="puntos">Parejas: 0/8</div><div id="btn"><button>JUGAR</button></div></div>',
        script=_SCRIPT_MEMORIA,
    )

def get_runner_html(titulo):
    return _BASE.format(
        titulo=titulo,
        estilos=_STYLE_RUNNER,
        body='<div id="c"><div id="jugador"></div><div id="puntos">0 m</div><div id="btn"><button>CORRER</button></div></div>',
        script=_SCRIPT_RUNNER,
    )

def get_trivial_html(tema):
    t = (tema or "cultura").strip().lower()
    preguntas = _TRIVIAL_PREGUNTAS.get(t, _TRIVIAL_PREGUNTAS.get("cultura", []))
    if not preguntas:
        preguntas = _TRIVIAL_PREGUNTAS["cultura"]
    import json
    preguntas_js = json.dumps(preguntas, ensure_ascii=False)
    return _BASE.format(
        titulo="Trivial: " + (tema or "Cultura").strip().title(),
        estilos=_STYLE_TRIVIAL,
        body='<div id="c"><div id="pregunta"></div><div id="opciones"></div><div id="puntos">0 / 0</div><div id="btn"><button>JUGAR</button></div><div id="fin" style="display:none;"></div></div>',
        script=_SCRIPT_TRIVIAL % preguntas_js,
    )

_TRIVIAL_PREGUNTAS = {
    "historia": [
        {"p": "En que ano cayo el Muro de Berlin?", "o": ["1987", "1989", "1991", "1985"], "c": 1},
        {"p": "Quien fue el primer rey de Espana unificada?", "o": ["Carlos I", "Felipe II", "Los Reyes Catolicos", "Carlos III"], "c": 2},
        {"p": "Que imperio construyo la Gran Muralla?", "o": ["Japones", "Mongol", "Chino", "Indio"], "c": 2},
        {"p": "En que siglo descubrio Colon America?", "o": ["XIV", "XV", "XVI", "XVII"], "c": 1},
        {"p": "Cual fue la capital del Imperio Romano de Oriente?", "o": ["Roma", "Atenas", "Constantinopla", "Alejandria"], "c": 2},
        {"p": "Quien escribio La Iliada?", "o": ["Virgilio", "Homero", "Sofocles", "Platon"], "c": 1},
    ],
    "deportes": [
        {"p": "Cuantos jugadores hay en un equipo de futbol en el campo?", "o": ["9", "10", "11", "12"], "c": 2},
        {"p": "En que pais nacio el tenis?", "o": ["Francia", "Inglaterra", "Espana", "USA"], "c": 1},
        {"p": "Cada cuantos anos se celebra el Mundial de futbol?", "o": ["2", "3", "4", "5"], "c": 2},
        {"p": "Que pais gano el Mundial 2022?", "o": ["Francia", "Brasil", "Argentina", "Alemania"], "c": 2},
        {"p": "Cual es el torneo de tenis mas antiguo?", "o": ["US Open", "Roland Garros", "Wimbledon", "Australia Open"], "c": 2},
        {"p": "En que deporte se usa un birdie?", "o": ["Tenis", "Badminton", "Padel", "Squash"], "c": 1},
    ],
    "geografia": [
        {"p": "Cual es el rio mas largo del mundo?", "o": ["Amazonas", "Nilo", "Misisipi", "Yangtse"], "c": 0},
        {"p": "Capital de Australia?", "o": ["Sydney", "Melbourne", "Canberra", "Brisbane"], "c": 2},
        {"p": "Cuantos oceanos hay?", "o": ["3", "4", "5", "6"], "c": 2},
        {"p": "Pais mas grande del mundo por superficie?", "o": ["China", "Canada", "Rusia", "USA"], "c": 2},
        {"p": "Donde esta el monte Everest?", "o": ["India", "Nepal/China", "Butan", "Pakistan"], "c": 1},
        {"p": "Cual es el pais mas poblado?", "o": ["India", "China", "USA", "Indonesia"], "c": 0},
    ],
    "ciencia": [
        {"p": "Formula del agua?", "o": ["CO2", "H2O", "O2", "H2O2"], "c": 1},
        {"p": "Planeta mas cercano al Sol?", "o": ["Venus", "Mercurio", "Marte", "Tierra"], "c": 1},
        {"p": "Velocidad de la luz aproximada (km/s)?", "o": ["150.000", "300.000", "450.000", "500.000"], "c": 1},
        {"p": "Quien formulo la teoria de la relatividad?", "o": ["Newton", "Einstein", "Hawking", "Bohr"], "c": 1},
        {"p": "Cuantos lados tiene un hexagono?", "o": ["5", "6", "7", "8"], "c": 1},
        {"p": "Elemento quimico con simbolo Au?", "o": ["Plata", "Oro", "Aluminio", "Argon"], "c": 1},
    ],
    "cultura": [
        {"p": "Quien pinto La Gioconda?", "o": ["Miguel Angel", "Rafael", "Leonardo da Vinci", "Donatello"], "c": 2},
        {"p": "Cual es el libro mas vendido de la historia?", "o": ["Don Quijote", "La Biblia", "Harry Potter", "Cien anios de soledad"], "c": 1},
        {"p": "En que ciudad esta la Torre Eiffel?", "o": ["Londres", "Berlin", "Paris", "Bruselas"], "c": 2},
        {"p": "Quien escribio Don Quijote?", "o": ["Lope de Vega", "Cervantes", "Quevedo", "Garcia Lorca"], "c": 1},
        {"p": "Cuantas cuerdas tiene una guitarra clasica?", "o": ["4", "5", "6", "7"], "c": 2},
        {"p": "Que premio gana el mejor director en Cannes?", "o": ["Oso de Oro", "Palma de Oro", "Leon de Oro", "Gran Premio"], "c": 1},
    ],
}

_STYLE_TRIVIAL = """
#c{width:min(100vw,420px);min-height:320px;padding:1.2rem;background:rgba(0,0,0,0.35);}
#pregunta{font-size:1.15rem;font-weight:600;margin-bottom:1rem;line-height:1.4;}
#opciones{display:flex;flex-direction:column;gap:10px;}
#opciones button{padding:14px 18px;text-align:left;background:rgba(79,195,247,0.15);border:2px solid rgba(79,195,247,0.5);border-radius:12px;color:#fff;font-size:1rem;cursor:pointer;}
#opciones button:hover{background:rgba(79,195,247,0.3);}
#opciones button.correcto{border-color:#4ade80;background:rgba(74,222,128,0.25);}
#opciones button.incorrecto{border-color:#ef4444;background:rgba(239,68,68,0.2);}
#puntos{position:absolute;top:12px;right:12px;font-weight:700;color:#4fc3f7;}
#btn{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);z-index:10;}
#btn button{padding:18px 36px;font-size:1.2rem;background:linear-gradient(135deg,#a78bfa,#7c3aed);border:none;border-radius:12px;color:#fff;font-weight:700;cursor:pointer;}
#fin{font-size:1.3rem;font-weight:700;text-align:center;padding:1rem;}
"""

_SCRIPT_TRIVIAL = """
var preguntas=%s;
var idx=0,puntos=0,btn=document.getElementById('btn'),fin=document.getElementById('fin');
function mostrar(){
document.getElementById('pregunta').textContent=(idx+1)+'. '+preguntas[idx].p;
var op=document.getElementById('opciones');op.innerHTML='';
for(var i=0;i<preguntas[idx].o.length;i++){
var b=document.createElement('button');b.textContent=preguntas[idx].o[i];b.dataset.i=i;
b.onclick=function(){var i=parseInt(this.dataset.i);var correcta=preguntas[idx].c;var btns=op.querySelectorAll('button');for(var j=0;j<btns.length;j++){btns[j].disabled=true;if(parseInt(btns[j].dataset.i)===correcta)btns[j].classList.add('correcto');else if(parseInt(btns[j].dataset.i)===i&&i!==correcta)btns[j].classList.add('incorrecto');}
if(i===correcta)puntos++;document.getElementById('puntos').textContent=puntos+' / '+(idx+1);
setTimeout(function(){idx++;if(idx>=preguntas.length){document.getElementById('c').querySelector('#pregunta,#opciones').innerHTML='';fin.style.display='block';fin.textContent='Resultado: '+puntos+' / '+preguntas.length;fin.style.color=puntos>=preguntas.length/2?'#4ade80':'#f59e0b';}else mostrar();},1200);};
op.appendChild(b);}
document.getElementById('puntos').textContent=puntos+' / '+(idx+1);
}
btn.querySelector('button').onclick=function(){idx=0;puntos=0;btn.style.display='none';fin.style.display='none';document.getElementById('puntos').textContent='0 / 0';mostrar();};
"""

_BASE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>{titulo}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:linear-gradient(180deg,#0a0a12 0%,#1a1a2e 50%,#16213e 100%);min-height:100vh;overflow:hidden;touch-action:manipulation;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;}}
h1{{font-size:clamp(1rem,4vw,1.4rem);margin-bottom:8px;}}
#c{{position:relative;border-radius:16px;overflow:hidden;border:2px solid rgba(79,195,247,0.35);box-shadow:0 0 50px rgba(79,195,247,0.12);}}
{estilos}
</style>
</head>
<body>
<h1>{titulo}</h1>
{body}
<script>{script}</script>
</body>
</html>"""

_STYLE_SHOOTER = """
#c{width:min(100vw,420px);height:min(75vh,560px);background:rgba(0,0,0,0.45);}
#nave{width:44px;height:44px;background:linear-gradient(135deg,#00d9ff,#0099cc);border-radius:10px;position:absolute;bottom:24px;left:50%;transform:translateX(-50%);box-shadow:0 0 20px rgba(0,217,255,0.5);transition:left 0.06s;}
#puntos{position:absolute;top:12px;left:12px;font-size:1.3rem;font-weight:700;color:#4fc3f7;z-index:10;}
#vidas{position:absolute;top:12px;right:12px;color:#ff6b6b;z-index:10;}
.bala{width:6px;height:14px;background:linear-gradient(#4fc3f7,#0288d1);border-radius:2px;position:absolute;}
.enemigo{width:32px;height:32px;background:linear-gradient(135deg,#ff6b6b,#c92a2a);border-radius:8px;position:absolute;}
#btn{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.75);z-index:20;}
#btn button{padding:16px 32px;font-size:1.2rem;background:linear-gradient(135deg,#4fc3f7,#0288d1);border:none;border-radius:12px;color:#fff;font-weight:700;cursor:pointer;}
#controles{display:flex;gap:16px;margin-top:10px;}
#controles button{width:64px;height:64px;border-radius:50%;background:rgba(79,195,247,0.25);border:2px solid rgba(79,195,247,0.6);color:#fff;font-size:1.4rem;cursor:pointer;}
"""

_STYLE_SNAKE = """
#c{width:min(90vw,380px);height:min(90vw,380px);background:#0d1b0d;display:flex;align-items:center;justify-content:center;}
#can{width:100%;height:100%;display:block;border-radius:8px;}
#puntos{position:absolute;top:10px;left:10px;font-weight:700;color:#4ade80;z-index:5;}
#btn{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);z-index:10;}
#btn button{padding:16px 32px;font-size:1.2rem;background:linear-gradient(135deg,#4ade80,#16a34a);border:none;border-radius:12px;color:#fff;font-weight:700;cursor:pointer;}
#controles{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;margin-top:10px;}
#controles button{width:56px;height:56px;border-radius:12px;background:rgba(74,222,128,0.25);border:2px solid #4ade80;color:#fff;font-size:1.2rem;cursor:pointer;}
"""

_STYLE_MEMORIA = """
#c{width:min(100vw,360px);padding:12px;background:rgba(0,0,0,0.3);}
#tablero{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;}
.carta{aspect-ratio:1;background:linear-gradient(135deg,#1e3a5f,#16213e);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.8rem;cursor:pointer;transition:transform 0.2s;}
.carta.volteada{background:linear-gradient(135deg,#4fc3f7,#0288d1);}
.carta.encontrada{visibility:hidden;}
#puntos{text-align:center;margin-top:10px;font-weight:700;}
#btn{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);z-index:10;}
#btn button{padding:16px 32px;font-size:1.2rem;background:linear-gradient(135deg,#a78bfa,#7c3aed);border:none;border-radius:12px;color:#fff;font-weight:700;cursor:pointer;}
"""

_STYLE_RUNNER = """
#c{width:min(100vw,400px);height:min(60vh,450px);background:linear-gradient(180deg,#1e3a2f 0%,#0d1b0d 100%);position:relative;overflow:hidden;}
#jugador{width:40px;height:50px;background:linear-gradient(135deg,#4ade80,#16a34a);position:absolute;bottom:80px;left:40px;border-radius:8px;}
.obs{position:absolute;background:#ef4444;border-radius:6px;}
#puntos{position:absolute;top:10px;right:10px;font-weight:700;color:#4ade80;z-index:5;}
#btn{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.8);z-index:10;}
#btn button{padding:16px 32px;font-size:1.2rem;background:linear-gradient(135deg,#4ade80,#16a34a);border:none;border-radius:12px;color:#fff;font-weight:700;cursor:pointer;}
"""

_SCRIPT_SHOOTER = """
var c=document.getElementById('c'),n=document.getElementById('nave'),pt=document.getElementById('puntos'),vd=document.getElementById('vidas'),btn=document.getElementById('btn'),ctr=document.getElementById('controles');
var puntos=0,vidas=3,jugando=false,nx=50,balas=[],enemigos=[],ancho=c.offsetWidth,alto=c.offsetHeight;
function px(v){return (v/100)*(ancho-44);}
function mover(d){if(!jugando)return;nx=Math.max(0,Math.min(100,nx+d));n.style.left=px(nx)+'px';}
function disparar(){if(!jugando||vidas<=0)return;var b=document.createElement('div');b.className='bala';b.x=px(nx)+18;b.y=alto-68;b.style.left=b.x+'px';b.style.top=b.y+'px';c.appendChild(b);balas.push(b);}
function crearEnemigo(){if(!jugando||vidas<=0)return;var e=document.createElement('div');e.className='enemigo';e.x=Math.random()*(ancho-32);e.y=-36;e.vy=1.8+Math.random()*1.2;e.style.left=e.x+'px';e.style.top=e.y+'px';c.appendChild(e);enemigos.push(e);}
function loop(){
if(!jugando)return;
for(var i=balas.length-1;i>=0;i--){var b=balas[i];b.y-=14;b.style.top=b.y+'px';if(b.y<-20){b.remove();balas.splice(i,1);continue;}
for(var j=enemigos.length-1;j>=0;j--){var ev=enemigos[j];if(b.y<ev.y+32&&b.y+14>ev.y&&b.x+6>ev.x&&b.x<ev.x+32){puntos+=10;pt.textContent=puntos;b.remove();balas.splice(i,1);ev.remove();enemigos.splice(j,1);break;}}}
for(var k=enemigos.length-1;k>=0;k--){var e=enemigos[k];e.y+=e.vy;e.style.top=e.y+'px';
if(e.y+32>alto-70&&e.y<alto-24&&e.x+32>px(nx)&&e.x<px(nx)+44){vidas--;vd.textContent=vidas;e.remove();enemigos.splice(k,1);if(vidas<=0){jugando=false;btn.style.display='flex';btn.querySelector('button').textContent='REINTENTAR ('+puntos+' pts)';}}
if(e.y>alto){e.remove();enemigos.splice(k,1);}}
requestAnimationFrame(loop);
}
c.addEventListener('touchmove',function(ev){ev.preventDefault();if(ev.touches[0].clientX<c.getBoundingClientRect().left+ancho/2)mover(-5);else mover(5);});
document.onkeydown=function(e){if(e.code==='ArrowLeft'){e.preventDefault();mover(-6);}if(e.code==='ArrowRight'){e.preventDefault();mover(6);}if(e.code==='Space'){e.preventDefault();disparar();}};
document.getElementById('izq').onclick=function(){mover(-8);};document.getElementById('der').onclick=function(){mover(8);};
document.getElementById('disparo').onclick=disparar;
btn.querySelector('button').onclick=function(){jugando=true;puntos=0;vidas=3;pt.textContent='0';vd.textContent='3';while(c.querySelector('.bala'))c.querySelector('.bala').remove();while(c.querySelector('.enemigo'))c.querySelector('.enemigo').remove();balas=[];enemigos=[];btn.style.display='none';ctr.style.display='flex';n.style.left=px(50)+'px';nx=50;loop();setInterval(crearEnemigo,950);};
"""

_SCRIPT_SNAKE = """
var can=document.getElementById('can'),ctx=can.getContext('2d'),pt=document.getElementById('puntos'),btn=document.getElementById('btn'),ctr=document.getElementById('controles');
var W=can.width=can.offsetWidth,H=can.height=can.offsetHeight,cel=Math.min(Math.floor(W/18),Math.floor(H/18)),cols=Math.floor(W/cel),fil=Math.floor(H/cel);
var snake=[{x:Math.floor(cols/2),y:Math.floor(fil/2)}],dir='R',food={x:0,y:0},puntos=0,jugando=false,timer;
function draw(){
ctx.fillStyle='#0d1b0d';ctx.fillRect(0,0,W,H);
for(var i=0;i<snake.length;i++){ctx.fillStyle=i===0?'#4ade80':'#22c55e';ctx.fillRect(snake[i].x*cel+1,snake[i].y*cel+1,cel-2,cel-2);}
ctx.fillStyle='#ef4444';ctx.beginPath();ctx.arc(food.x*cel+cel/2,food.y*cel+cel/2,cel/2-2,0,6.28);ctx.fill();
}
function nuevaComida(){do{food.x=Math.floor(Math.random()*cols);food.y=Math.floor(Math.random()*fil);}while(snake.some(function(s){return s.x===food.x&&s.y===food.y;}));}
function step(){
if(!jugando)return;
var h=snake[0],nx=h.x,ny=h.y;
if(dir==='R')nx++;if(dir==='L')nx--;if(dir==='U')ny--;if(dir==='D')ny++;
if(nx<0||nx>=cols||ny<0||ny>=fil||snake.some(function(s){return s.x===nx&&s.y===ny;})){jugando=false;btn.style.display='flex';btn.querySelector('button').textContent='REINTENTAR ('+puntos+')';return;}
snake.unshift({x:nx,y:ny});
if(nx===food.x&&ny===food.y){puntos++;pt.textContent=puntos;nuevaComida();}else snake.pop();
draw();setTimeout(step,120);
}
document.getElementById('izq').onclick=function(){if(dir!=='R')dir='L';};
document.getElementById('der').onclick=function(){if(dir!=='L')dir='R';};
document.getElementById('arriba').onclick=function(){if(dir!=='D')dir='U';};
document.getElementById('abajo').onclick=function(){if(dir!=='U')dir='D';};
document.onkeydown=function(e){e.preventDefault();if(e.code==='ArrowLeft'&&dir!=='R')dir='L';if(e.code==='ArrowRight'&&dir!=='L')dir='R';if(e.code==='ArrowUp'&&dir!=='D')dir='U';if(e.code==='ArrowDown'&&dir!=='U')dir='D';};
btn.querySelector('button').onclick=function(){var box=can.parentElement;can.width=box.clientWidth;can.height=box.clientHeight;W=can.width;H=can.height;cel=Math.min(Math.floor(W/18),Math.floor(H/18));cols=Math.floor(W/cel);fil=Math.floor(H/cel);snake=[{x:Math.floor(cols/2),y:Math.floor(fil/2)}];dir='R';puntos=0;pt.textContent='0';nuevaComida();jugando=true;btn.style.display='none';ctr.style.display='grid';draw();step();};
"""

_SCRIPT_MEMORIA = """
var emojis=['🍎','🍊','🍋','🍇','🍓','🍑','🍒','🥝'];
var cartas=[],volteadas=[],pares=0,bloqueado=false;
function init(){var valores=emojis.concat(emojis);for(var i=valores.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=valores[i];valores[i]=valores[j];valores[j]=t;}
var tb=document.getElementById('tablero'),pt=document.getElementById('puntos'),btn=document.getElementById('btn');
tb.innerHTML='';cartas=[];volteadas=[];pares=0;bloqueado=false;
for(var i=0;i<16;i++){var div=document.createElement('div');div.className='carta';div.dataset.i=i;div.dataset.val=valores[i];div.textContent='?';div.onclick=function(){if(bloqueado)return;var d=this;if(d.classList.contains('volteada')||d.classList.contains('encontrada'))return;d.textContent=d.dataset.val;d.classList.add('volteada');volteadas.push(d);if(volteadas.length===2){bloqueado=true;if(volteadas[0].dataset.val===volteadas[1].dataset.val){pares++;pt.textContent='Parejas: '+pares+'/8';volteadas[0].classList.add('encontrada');volteadas[1].classList.add('encontrada');if(pares===8){setTimeout(function(){alert('¡Completado!');},300);}bloqueado=false;}else setTimeout(function(){volteadas[0].textContent='?';volteadas[1].textContent='?';volteadas[0].classList.remove('volteada');volteadas[1].classList.remove('volteada');volteadas=[];bloqueado=false;},600);}volteadas=volteadas.slice(-2);}};tb.appendChild(div);}
pt.textContent='Parejas: 0/8';btn.style.display='none';}
document.getElementById('btn').querySelector('button').onclick=function(){document.getElementById('btn').style.display='none';init();};
"""

_SCRIPT_RUNNER = """
var c=document.getElementById('c'),j=document.getElementById('jugador'),pt=document.getElementById('puntos'),btn=document.getElementById('btn');
var dist=0,jugando=false,obs=[],vel=6,alturaJ=80;
function loop(){
if(!jugando)return;
dist+=0.5;pt.textContent=Math.floor(dist)+' m';
j.style.bottom=alturaJ+'px';
for(var i=obs.length-1;i>=0;i--){obs[i].x-=vel;obs[i].style.left=obs[i].x+'px';if(obs[i].x<-50){obs[i].remove();obs.splice(i,1);}
var jl=40,jr=80,jb=alturaJ,jt=alturaJ+50;var ol=obs[i].x,or=obs[i].x+40,ob=parseInt(obs[i].style.bottom),ot=ob+35;
if(jr>ol&&jl<or&&jt>ob&&jb<ot){jugando=false;btn.style.display='flex';btn.querySelector('button').textContent='REINTENTAR ('+Math.floor(dist)+' m)';return;}}
if(Math.random()<0.02){var o=document.createElement('div');o.className='obs';o.style.width='40px';o.style.height='35px';o.style.bottom=alturaJ+'px';o.style.left=c.offsetWidth+20+'px';o.x=c.offsetWidth+20;c.appendChild(o);obs.push(o);}
requestAnimationFrame(loop);
}
document.onkeydown=function(e){if(e.code==='Space'){e.preventDefault();if(alturaJ===80){alturaJ=140;setTimeout(function(){alturaJ=80;},450);}}};
c.onclick=function(){if(alturaJ===80){alturaJ=140;setTimeout(function(){alturaJ=80;},450);}};
btn.querySelector('button').onclick=function(){while(c.querySelector('.obs'))c.querySelector('.obs').remove();obs=[];dist=0;alturaJ=80;jugando=true;btn.style.display='none';loop();};
"""