import {test} from 'node:test'
import assert from 'node:assert/strict'
import {normaliseName,validName} from '../src/utils/profileNames.js'
test('name formatting removes edges, repeated spaces and hyphens',()=>{
 assert.equal(normaliseName('  ANNE--MARIE   SMITH '),'Anne Marie Smith')
 assert.equal(normaliseName('josé'),'José')
 assert.equal(validName("O'Connor"),false)
 assert.equal(validName('Name2'),false)
})
