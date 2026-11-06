import {test} from 'node:test'
import assert from 'node:assert/strict'
// Quality policy is tested separately from the model loader.
import {readFileSync} from 'node:fs'
const source=readFileSync(new URL('../src/utils/selfieFaceDetection.js',import.meta.url),'utf8')
const policy=source.slice(source.indexOf('export function assessSelfie'))
const {assessSelfie}=await import('data:text/javascript,'+encodeURIComponent(policy))
const box={xCenter:.5,yCenter:.37,width:.4,height:.45,rotation:0}
test('zero and multiple faces cannot capture',()=>{
 assert.equal(assessSelfie([],null).ready,false)
 assert.match(assessSelfie([{boundingBox:box},{boundingBox:box}],null).message,/Multiple faces/)
})
test('distance, centring and stability checks',()=>{
 assert.equal(assessSelfie([{boundingBox:{...box,width:.15,height:.15}}],null,box).message,'Move closer')
 assert.equal(assessSelfie([{boundingBox:{...box,height:.8}}],null,box).message,'Move further away')
 assert.equal(assessSelfie([{boundingBox:box}],null).ready,false)
 assert.equal(assessSelfie([{boundingBox:box}],null,box).ready,true)
 assert.equal(assessSelfie([{boundingBox:{...box,xCenter:.9}}],null,box).ready,false)
})

test('allows comfortable off-centre positioning and slight hand movement',()=>{
 const relaxed={...box,xCenter:.67,yCenter:.58,width:.30,height:.38,rotation:.25}
 assert.equal(assessSelfie([{boundingBox:relaxed}],null,{...relaxed,xCenter:.64,yCenter:.57}).ready,true)
})
test('still rejects cropped faces, large movement and unreadably soft frames',()=>{
 const cropped={...box,xCenter:.75,width:.6}
 assert.equal(assessSelfie([{boundingBox:cropped}],null,cropped).ready,false)
 assert.equal(assessSelfie([{boundingBox:box}],null,{...box,xCenter:.3}).ready,false)
 const data=new Uint8ClampedArray(80*100*4).fill(128)
 assert.match(assessSelfie([{boundingBox:box}],{width:80,height:100,data},box).message,/focuses/)
})
