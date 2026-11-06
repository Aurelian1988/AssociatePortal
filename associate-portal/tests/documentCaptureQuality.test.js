import {test} from 'node:test'
import assert from 'node:assert/strict'
import {assessDocumentFrame} from '../src/utils/documentCaptureQuality.js'
function fixture(background=40){
 const width=320,height=240,data=new Uint8ClampedArray(width*height*4)
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  let shade=background
  if(x>=26&&x<=294&&y>=35&&y<=204)shade=220
  if(y>70&&y<170&&y%14<3&&x>80&&x<240)shade=60
  const i=(y*width+x)*4;data[i]=data[i+1]=data[i+2]=shade;data[i+3]=255
 }
 return {width,height,data}
}
test('clear aligned document is ready immediately without a previous frame',()=>{
 const frame=fixture(),first=assessDocumentFrame(frame)
 assert.equal(first.ready,true)
 const second=assessDocumentFrame(frame,first.gray)
 assert.equal(second.ready,true)
})
test('blank dark and overexposed frames never autocapture',()=>{
 for(const value of [10,255]){
  const frame={width:320,height:240,data:new Uint8ClampedArray(320*240*4).fill(value)}
  const first=assessDocumentFrame(frame)
  assert.equal(assessDocumentFrame(frame,first.gray).ready,false)
 }
})

function scaledCard(scale,shiftX=0){
 const width=320,height=240,data=new Uint8ClampedArray(width*height*4)
 const cw=width*scale,ch=cw/1.586,left=(width-cw)/2+shiftX,top=(height-ch)/2
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  let shade=40
  if(x>=left&&x<=left+cw&&y>=top&&y<=top+ch){
   shade=220
   if(x>left+cw*.2&&x<left+cw*.8&&y>top+ch*.2&&y<top+ch*.8&&y%14<3)shade=60
  }
  const i=(y*width+x)*4;data[i]=data[i+1]=data[i+2]=shade;data[i+3]=255
 }
 return {width,height,data}
}
test('clear smaller card and slight offset are accepted',()=>{
 for(const frame of [scaledCard(.66),scaledCard(.7,30)]){
  const first=assessDocumentFrame(frame)
  assert.equal(assessDocumentFrame(frame,first.gray).ready,true)
 }
})
test('a sharp frame does not wait for inter-frame movement to settle',()=>{
 const first=assessDocumentFrame(fixture())
 assert.equal(assessDocumentFrame(scaledCard(.7,20),first.gray).ready,true)
})
test('documents still cannot be too small or cut off',()=>{
 for(const frame of [scaledCard(.5),scaledCard(.98)]){
  const first=assessDocumentFrame(frame)
  assert.equal(assessDocumentFrame(frame,first.gray).ready,false)
 }
})

test('manual capture can use a clear frame without passing the movement timer',()=>{
 const first=assessDocumentFrame(fixture())
 assert.equal(first.ready,true)
 assert.equal(first.qualityReady,true)
 assert.ok(first.bounds)
 const dark={width:320,height:240,data:new Uint8ClampedArray(320*240*4).fill(10)}
 assert.equal(!!assessDocumentFrame(dark).qualityReady,false)
 assert.equal(!!assessDocumentFrame(scaledCard(.5)).qualityReady,false)
})

test('heavy shadows block automatic capture',()=>{
 const frame=fixture()
 for(let y=35;y<204;y++)for(let x=26;x<160;x++){
  const i=(y*frame.width+x)*4
  for(let c=0;c<3;c++)frame.data[i+c]*=.35
 }
 const result=assessDocumentFrame(frame)
 assert.equal(result.ready,false)
 assert.match(result.message,/shadow/)
})
test('sharp outer edges cannot compensate for unreadable document interior',()=>{
 const frame=fixture()
 for(let y=36;y<204;y++)for(let x=27;x<294;x++){
  const i=(y*frame.width+x)*4
  if(frame.data[i]===60)frame.data[i]=frame.data[i+1]=frame.data[i+2]=218
 }
 const result=assessDocumentFrame(frame)
 assert.equal(result.ready,false)
 assert.match(result.message,/focus/)
})

test('licence table lines do not replace faint outer edges',()=>{
 const width=320,height=240,data=new Uint8ClampedArray(width*height*4)
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  let shade=150
  if(x>=30&&x<=290&&y>=38&&y<=202)shade=170
  if(x>=80&&x<=240&&y>=70&&y<=170&&y%14<3)shade=30
  const i=(y*width+x)*4;data[i]=data[i+1]=data[i+2]=shade;data[i+3]=255
 }
 const result=assessDocumentFrame({width,height,data})
 assert.equal(result.ready,true)
 assert.ok(result.bounds.top<.18)
 assert.ok(result.bounds.bottom>.8)
})
