export function fnolUrl(values={}) {
 const url=new URL('https://forms.onemotion.co.uk/231143504881047')
 const put=(key,value)=>{if(value!==undefined&&value!==null&&String(value).trim())url.searchParams.set(key,String(value).trim())}
 put('name[first]',[values.first_name,values.middle_name].filter(Boolean).join(' ').replace(/\s+/g,' '))
 put('name[last]',values.last_name);put('email',values.email);put('telephoneNumber',values.mobile)
 for(const [target,source] of [['addr_line1','street_address'],['addr_line2','address_line_2'],['city','city'],['state','state_region'],['postal','postal_code']])put('address['+target+']',values[source])
 const date=(key,value)=>{const match=/^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value||''));if(match){put(key+'[day]',match[3]);put(key+'[month]',match[2]);put(key+'[year]',match[1])}}
 date('dateOf',values.dob)
 // Temporary mapping requested by the user: use licence issue date for this form field.
 date('drivingLicence',values.dl_issue_date)
 return url.toString()
}
