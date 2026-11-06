import base from './vite.config.js'
export default {...base,build:{...base.build,reportCompressedSize:false,outDir:'../erp-test-build'}}
