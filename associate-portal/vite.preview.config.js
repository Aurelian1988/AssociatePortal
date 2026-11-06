import base from './vite.config.js'
import path from 'path'
export default {...base,resolve:{...base.resolve,alias:{'@/data/agreements':path.resolve('../preview/agreements.js'),'@/data/onboarding':path.resolve('../preview/onboarding.js'),...base.resolve.alias}},build:{...base.build,reportCompressedSize:false,outDir:'../preview-build'}}
