import {test} from 'node:test'
import assert from 'node:assert/strict'
import {documentCropRect} from '../src/utils/documentBackground.js'
test('crop centres document with equal safety bleed and includes bottom edge',()=>{
 const rect=documentCropRect(1000,1400,{left:.1,right:.8,top:.15,bottom:.85})
 assert.ok(rect.left<100&&rect.top<210)
 assert.ok(rect.left+rect.width>800&&rect.top+rect.height>1190)
 assert.ok(rect.width<1000&&rect.height<1400)
 assert.ok(Math.abs(rect.left+rect.width/2-450)<=1)
})
test('bleed never samples beyond the captured frame',()=>{
 const r=documentCropRect(1000,1400,{left:.01,right:.99,top:.01,bottom:.99})
 assert.deepEqual(r,{left:0,top:0,width:1000,height:1400})
})
