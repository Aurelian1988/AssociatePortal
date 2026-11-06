let loading
const base=`${import.meta.env.BASE_URL}vendor/face-detection/`
export async function createFaceDetector(onResults) {
  if(!loading)loading=new Promise((resolve,reject)=>{
    if(window.FaceDetection)return resolve()
    const script=document.createElement('script');script.src=base+'face_detection.js'
    script.onload=resolve;script.onerror=()=>{loading=null;script.remove();reject(new Error('Face detection could not load. Check your connection and try again.'))}
    document.head.appendChild(script)
  })
  await loading
  const model=new window.FaceDetection({locateFile:file=>base+file})
  model.setOptions({model:'short',minDetectionConfidence:.6,selfieMode:false})
  model.onResults(onResults)
  return model
}
export function assessSelfie(detections, image, previousBox) {
  if(!detections.length)return {ready:false,message:'Keep your head inside the blue frame'}
  if(detections.length!==1)return {ready:false,message:'Multiple faces detected. Please ensure only you are in the frame.'}
  const box=detections[0].boundingBox
  if(box.height<.24||box.width<.22)return {ready:false,message:'Move closer',box}
  if(box.height>.75||box.width>.80)return {ready:false,message:'Move further away',box}
  if(box.xCenter-box.width/2<.02||box.xCenter+box.width/2>.98||box.yCenter-box.height/2<.02||box.yCenter+box.height/2>.94||Math.abs(box.xCenter-.5)>.20||Math.abs(box.yCenter-.42)>.23)return {ready:false,message:'Centre your face and keep your shoulders in view',box}
  if(Math.abs(box.rotation||0)>.30)return {ready:false,message:'Keep your head upright',box}
  if(image){
    const {data,width:w,height:h}=image
    const left=Math.max(1,Math.floor((box.xCenter-box.width/2)*w)),right=Math.min(w-2,Math.ceil((box.xCenter+box.width/2)*w))
    const top=Math.max(1,Math.floor((box.yCenter-box.height/2)*h)),bottom=Math.min(h-2,Math.ceil((box.yCenter+box.height/2)*h))
    const gray=(x,y)=>{const i=(y*w+x)*4;return .299*data[i]+.587*data[i+1]+.114*data[i+2]}
    let brightness=0,sharp=0,count=0
    for(let y=top;y<bottom;y++)for(let x=left;x<right;x++){
      const v=gray(x,y);brightness+=v
      const lap=4*v-gray(x-1,y)-gray(x+1,y)-gray(x,y-1)-gray(x,y+1);sharp+=lap*lap;count++
    }
    if(!count||brightness/count<45)return {ready:false,message:'Add more light to your face',box}
    if(brightness/count>240)return {ready:false,message:'Move away from strong light',box}
    if(sharp/count<45)return {ready:false,message:'Keep steady while the camera focuses',box}
  }
  if(!previousBox||Math.abs(previousBox.xCenter-box.xCenter)+Math.abs(previousBox.yCenter-box.yCenter)+Math.abs(previousBox.width-box.width)>.06)return {ready:false,message:'Hold steady',box}
  return {ready:true,message:'Perfect! You can take the photo.',box}
}
