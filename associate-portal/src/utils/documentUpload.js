// Upload progress is measured; OCR progress is unknown until the server replies.
export function uploadDocument(params,onProgress){
 return new Promise((resolve,reject)=>{
  const xhr=new XMLHttpRequest()
  xhr.open('POST','/api/method/onemotion.api.profile_documents.upload_profile_document')
  xhr.withCredentials=true;xhr.timeout=120000
  xhr.setRequestHeader('Accept','application/json')
  xhr.setRequestHeader('Content-Type','application/json; charset=utf-8')
  xhr.setRequestHeader('X-Frappe-Site-Name',window.location.hostname)
  if(window.csrf_token&&window.csrf_token!=='{{ csrf_token }}')xhr.setRequestHeader('X-Frappe-CSRF-Token',window.csrf_token)
  xhr.upload.onprogress=e=>onProgress({stage:'uploading',percent:e.lengthComputable?Math.min(100,Math.round(e.loaded/e.total*100)):null})
  xhr.upload.onload=()=>onProgress({stage:'reading',percent:null})
  xhr.onerror=()=>reject(new Error('The connection was interrupted. Please try again.'))
  xhr.ontimeout=()=>reject(new Error('Document reading took too long. Please try again.'))
  xhr.onabort=()=>reject(new Error('Upload cancelled.'))
  xhr.onload=()=>{
   let data
   try{data=JSON.parse(xhr.responseText)}catch{reject(new Error('Could not read the server response. Please try again.'));return}
   if(xhr.status>=200&&xhr.status<300){resolve(data.message??data);return}
   let message='The document could not be read. Please try a clear photo.'
   try{const messages=JSON.parse(data._server_messages||'[]');if(messages[0])message=JSON.parse(messages[0]).message||message}catch{}
   reject(new Error(message))
  }
  xhr.send(JSON.stringify(params))
 })
}
