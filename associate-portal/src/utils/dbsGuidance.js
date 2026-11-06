export function disclosureRegion(address) {
  const text = [address.country,address.state_region].filter(Boolean).join(' ').toLowerCase()
  if (/\bnorthern ireland\b/.test(text)) return 'ni'
  if (/\bscotland\b/.test(text)) return 'scotland'
  return 'england-wales'
}
export const disclosureGuidance = {
  'england-wales': {
    title:'Basic DBS check — England and Wales',
    url:'https://www.gov.uk/request-copy-criminal-record',
    summary:'A basic DBS check shows unspent convictions and conditional cautions. Apply using GOV.UK One Login. Have your addresses for the last five years and the dates you lived there ready, plus your passport, driving licence and National Insurance number if you have them.',
    share:'When your result is available, use the online sharing option, enter dbs@onemotion.co.uk as the recipient and send us the one-time share code and reference number. Online sharing is available only for eligible results; if no share code is offered, contact your team.'
  },
  scotland: {
    title:'Level 1 disclosure — Scotland',
    url:'https://www.mygov.scot/basic-disclosure/apply-for-basic-disclosure/',
    summary:'Basic disclosure is now called Level 1 disclosure. Apply through ScotAccount, track the application and wait for the email telling you that your result is ready. Sign in to view and share your disclosure with the organisation.',
    share:'Follow the service’s sharing instructions. If asked for the recipient email, use dbs@onemotion.co.uk. Enter a share code if the service issues one. If it shares directly without a code, contact your team; do not enter an application reference as a share code.'
  },
  ni: {
    title:'AccessNI — Northern Ireland',
    url:'https://www.nidirect.gov.uk/campaigns/accessni-criminal-record-checks',
    summary:'Use AccessNI for a criminal record check for a role in Northern Ireland. Individuals can apply for a basic check online using a nidirect account. Follow the service’s application and result-sharing instructions.',
    share:'If prompted to share with an email address, use dbs@onemotion.co.uk. Enter the share code if one is issued. If the service shares the certificate directly without a code, contact your team.'
  }
}
