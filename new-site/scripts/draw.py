from pathlib import Path
P=Path(__file__).resolve().parents[1]/'assets'
# Original vector technical illustrations, deliberately identified as diagrams in the UI.
shapes={
'lyra':'<path d="M195 55 105 390 M205 55 295 390 M200 95 267 370 M200 45V295 M130 250H270 M150 135H250"/><path d="M128 256h145v13H128z"/>',
'studio':'<path d="M145 65V350 M255 65V350 M145 85H255 M145 320H255 M200 30V295 M130 355H280L305 390H105Z M125 235H275v18H125Z"/>',
'clapper':'<path d="M140 105 110 390 M260 105 290 390 M260 110 318 367 M140 110H260V298H140Z M130 300H272v16H130Z"/><path d="M155 125h90v158h-90z" fill="#eee3cd"/>',
'desktop':'<path d="M195 100 100 335 M205 100 300 335 M200 130 280 325 M200 85V280 M125 255H275v15H125Z M160 145H240"/>',
'box':'<path d="m90 255 210-135 105 110-210 138Z M90 255v55l105 80v-22 M195 368l210-138v55L195 390 M213 195l120 83 M175 220l120 85 M224 346v24l100-65v-23"/>',
'expo':'<path d="M160 80 130 390 M245 80 275 390 M245 90 310 365 M160 90H245 M145 270H260v17H145Z M160 120H245V250H160Z"/>',
'frame':'<path d="M150 70V330 M255 70V330 M150 80H255 M130 330H275L295 380H110Z"/>',
' table':'',
' table2':'',
' table3':'',
' table4':'',
'table':'<path d="M85 180 240 130 330 185 170 240Z M100 196v175 M170 240v155 M315 194v177 M112 340l55 35 140-41 M240 143V75 M170 90l140-40v130"/>',
'rack':'<path d="M100 170 290 130 325 300 130 355Z M100 170v158l30 27 M115 195l175-38 M122 225l175-38 M128 255l175-38 M134 285l175-38 M100 328v55 M130 355v35 M325 300v70"/>',
'transformer':'<path d="M100 190 245 95 315 165 170 260Z M118 205l-5 180 M170 260v135 M300 180v205 M113 355h185 M200 240v100"/>'}
for k,v in shapes.items():
 if not v:continue
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 440"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#ceaa7c"/><stop offset="1" stop-color="#99754d"/></linearGradient></defs><ellipse cx="211" cy="398" rx="125" ry="13" fill="#34483d" opacity=".07"/><g fill="none" stroke="url(#g)" stroke-width="13" stroke-linejoin="round" stroke-linecap="round">{v}</g><g fill="#554a36"><circle cx="200" cy="250" r="4"/><circle cx="200" cy="140" r="4"/></g></svg>'
 (P/(k+'.svg')).write_text(svg)
(P/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#34483d"/><path d="m12 36 12-26 12 26M17 26h14M24 8v22" stroke="#f8f4ec" stroke-width="3" fill="none"/></svg>')
