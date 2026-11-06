export const nameFields = new Set(['first_name','middle_name','last_name','mothers_first_name','mothers_maiden_name'])
export function normaliseName(value) {
  return String(value || '').normalize('NFC').replace(/\p{Pd}/gu,' ').trim().replace(/\s+/g,' ').toLocaleLowerCase().replace(/(^|\s)(\p{L})/gu,(_,space,letter)=>space+letter.toLocaleUpperCase())
}
export const validName = value => /^[\p{L}\p{M}\s]*$/u.test(String(value || ''))
