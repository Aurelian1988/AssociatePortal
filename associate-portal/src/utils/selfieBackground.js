// MediaPipe assets are served by this app; photos never leave the device for processing.
let loading
const base = `${import.meta.env.BASE_URL}vendor/selfie-segmentation/`
function loadModel() {
  if (!loading) loading = new Promise((resolve, reject) => {
    if (window.SelfieSegmentation) return resolve()
    const script = document.createElement('script')
    script.src = base + 'selfie_segmentation.js'
    script.onload = resolve
    script.onerror = () => { script.remove(); loading = null; reject(new Error('Could not load background blur. Try again.')) }
    document.head.appendChild(script)
  })
  return loading
}
export async function blurSelfieBackground(source) {
  await loadModel()
  const model = new window.SelfieSegmentation({ locateFile: file => base + file })
  model.setOptions({ modelSelection: 0, selfieMode: false })
  const result = document.createElement('canvas')
  result.width = source.width; result.height = source.height
  const context = result.getContext('2d')
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Background blur timed out. Try again.')), 20000)
      model.onResults(({ segmentationMask }) => {
        try {
          // Foreground remains sharp. Blur applies only behind the person.
          context.drawImage(segmentationMask, 0, 0, result.width, result.height)
          context.globalCompositeOperation = 'source-in'
          context.drawImage(source, 0, 0)
          context.globalCompositeOperation = 'destination-over'
          context.filter = 'blur(16px)'
          context.drawImage(source, -24, -24, result.width + 48, result.height + 48)
          context.filter = 'none'; context.globalCompositeOperation = 'source-over'
          clearTimeout(timer); resolve()
        } catch (error) { clearTimeout(timer); reject(error) }
      })
      model.send({ image: source }).catch(error => { clearTimeout(timer); reject(error) })
    })
    return result
  } finally { await model.close() }
}
