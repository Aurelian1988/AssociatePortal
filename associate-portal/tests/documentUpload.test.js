import {test} from 'node:test'
import assert from 'node:assert/strict'
import {uploadDocument} from '../src/utils/documentUpload.js'
function mock(){
 let request
 globalThis.window={location:{hostname:'portal.test'},csrf_token:'test-token'}
 globalThis.XMLHttpRequest=class{
  constructor(){request=this;this.upload={};this.headers={}}
  open(method,url){this.method=method;this.url=url}
  setRequestHeader(k,v){this.headers[k]=v}
  send(body){this.body=JSON.parse(body)}
 }
 return ()=>request
}
test('upload percentage is real; OCR uses an indeterminate phase until response',async()=>{
 const request=mock(),updates=[]
 const promise=uploadDocument({kind:'passport',image_base64:'test'},p=>updates.push(p));const r=request()
 assert.equal(r.headers['X-Frappe-CSRF-Token'],'test-token')
 r.upload.onprogress({lengthComputable:true,loaded:20,total:100})
 r.upload.onload()
 assert.deepEqual(updates,[{stage:'uploading',percent:20},{stage:'reading',percent:null}])
 r.status=200;r.responseText=JSON.stringify({message:{suggestions:{}}});r.onload()
 assert.deepEqual(await promise,{suggestions:{}})
})
test('unreadable document rejection is displayed and does not become success',async()=>{
 const request=mock(),promise=uploadDocument({},()=>{}),r=request()
 r.status=422;r.responseText=JSON.stringify({_server_messages:JSON.stringify([JSON.stringify({message:'Retake in better light.'})])});r.onload()
 await assert.rejects(promise,/Retake in better light/)
})
