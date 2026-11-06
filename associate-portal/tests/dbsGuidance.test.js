import {test} from 'node:test'
import assert from 'node:assert/strict'
import {disclosureRegion,disclosureGuidance} from '../src/utils/dbsGuidance.js'
test('address-based disclosure links',()=>{
 assert.equal(disclosureRegion({country:'Scotland'}),'scotland')
 assert.equal(disclosureRegion({country:'United Kingdom',state_region:'Northern Ireland'}),'ni')
 assert.equal(disclosureRegion({country:'United Kingdom',street_address:'Scotland Road'}),'england-wales')
 assert.equal(disclosureRegion({country:'Wales'}),'england-wales')
 for(const guide of Object.values(disclosureGuidance)) assert.match(guide.share,/dbs@onemotion.co.uk/)
})
