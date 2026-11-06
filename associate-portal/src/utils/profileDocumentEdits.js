export function normaliseDocumentValue(key,value){
 const text=String(value??'').trim()
 if(['passport_number','dl_number','postal_code'].includes(key))return text.replace(/\s+/g,'').toUpperCase()
 if(key==='dob'||key.endsWith('_date')||key==='dl_photocard_expiry')return text.slice(0,10)
 return (text.normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}]+/gu)||[]).join(' ')
}
