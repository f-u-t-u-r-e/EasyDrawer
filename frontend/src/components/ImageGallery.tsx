import React from 'react'
import { Download, Star, Wand2 } from 'lucide-react'
import type { GeneratedImage } from '@/types/api'

const VARIANT_LABELS = ['构图', '光影', '细节']

interface ImageGalleryProps {
  images: GeneratedImage[]
  bestImageSeed: number
  onImageClick: (image: GeneratedImage) => void
}

export const ImageGallery: React.FC<ImageGalleryProps> = ({
  images,
  bestImageSeed,
  onImageClick,
}) => {
  const downloadImage = (image: GeneratedImage, e: React.MouseEvent) => {
    e.stopPropagation()
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${image.image_data}`
    link.download = `easydrawer-${image.seed}.png`
    link.click()
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {images.map((image, idx) => {
        const isBest =
          image.seed === bestImageSeed &&
          image.quality_score === Math.max(...images.map((i) => i.quality_score || 0))

        return (
          <div
            key={`${image.seed}-${idx}`}
            className={`image-card group ${isBest ? 'ring-2 ring-amber-400/60' : ''}`}
            onClick={() => onImageClick(image)}
          >
            <img
              src={`data:image/png;base64,${image.image_data}`}
              alt={`生成图片 ${idx + 1}`}
              className="w-full h-64 object-cover"
            />

            {/* 顶部标签 */}
            <div className="absolute top-2.5 left-2.5 flex gap-1.5">
              {image.variant_index !== undefined && image.variant_index < VARIANT_LABELS.length && (
                <span
                  className="px-2 py-0.5 text-[10px] rounded-md font-medium text-white"
                  style={{ background: 'rgba(245, 158, 11, 0.7)', backdropFilter: 'blur(4px)' }}
                >
                  {VARIANT_LABELS[image.variant_index]}
                </span>
              )}
              {image.is_refined && (
                <span
                  className="px-2 py-0.5 text-[10px] rounded-md font-medium text-white flex items-center gap-0.5"
                  style={{ background: 'rgba(244, 63, 94, 0.7)', backdropFilter: 'blur(4px)' }}
                >
                  <Wand2 className="w-2.5 h-2.5" />
                  精修
                </span>
              )}
            </div>

            {/* 最佳标记 */}
            {isBest && (
              <div className="absolute top-2.5 right-2.5">
                <span
                  className="flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-md font-semibold text-amber-300"
                  style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)', border: '1px solid rgba(245, 158, 11, 0.3)' }}
                >
                  <Star className="w-2.5 h-2.5 fill-current" />
                  最佳
                </span>
              </div>
            )}

            {/* 渐变遮罩 */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            {/* 底部信息 */}
            <div className="absolute bottom-0 left-0 right-0 p-3.5 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  {image.quality_score != null && (
                    <div className="text-sm text-amber-400 font-semibold">
                      {image.quality_score.toFixed(1)}
                      <span className="text-[10px] text-slate-400 ml-1 font-normal">分</span>
                    </div>
                  )}
                  <div className="text-[10px] text-slate-400">
                    seed: {image.seed}
                  </div>
                </div>

                <button
                  onClick={(e) => downloadImage(image, e)}
                  className="p-2 rounded-lg transition-all hover:scale-110"
                  style={{ background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.2)' }}
                >
                  <Download className="w-3.5 h-3.5 text-amber-400" />
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
