// Preserve every captured pixel: crop with bleed, never blur document evidence.
export function documentCropRect(width,height,bounds,bleed=.08){
  const padX=(bounds.right-bounds.left)*width*bleed
  const padY=(bounds.bottom-bounds.top)*height*bleed
  const left=Math.max(0,Math.floor(bounds.left*width-padX))
  const top=Math.max(0,Math.floor(bounds.top*height-padY))
  const right=Math.min(width,Math.ceil(bounds.right*width+padX))
  const bottom=Math.min(height,Math.ceil(bounds.bottom*height+padY))
  return {left,top,width:right-left,height:bottom-top}
}
export function cropDocument(source,bounds){
  const rect=documentCropRect(source.width,source.height,bounds)
  const canvas=document.createElement('canvas');canvas.width=rect.width;canvas.height=rect.height
  canvas.getContext('2d').drawImage(source,rect.left,rect.top,rect.width,rect.height,0,0,rect.width,rect.height)
  return canvas
}
