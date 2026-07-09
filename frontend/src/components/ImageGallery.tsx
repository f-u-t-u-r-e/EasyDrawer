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
  onImageClick
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
        const isBest = image.seed === bestImageSeed && image.quality_score === Math.max(...images.map(i => i.quality_score || 0))

        return (
          <div
            key={`${image.seed}-${idx}`}
            className={`image-card ${isBest ? 'ring-2 ring-yellow-400' : ''}`}
            onClick={() => onImageClick(image)}
          >
            <img
              src={`data:image/png;base64,${image.image_data}`}
              alt={`生成图片 ${idx + 1}`}
              className="w-full h-64 object-cover"
            />

            {/* 顶部标签 */}
            <div className="absolute top-2 left-2 flex gap-1.5">
              {image.variant_index !== undefined && image.variant_index < VARIANT_LABELS.length && (
                <span className="px-1.5 py-0.5 bg-blue-500/80 text-white text-[10px] rounded">
                  {VARIANT_LABELS[image.variant_index]}
                </span>
              )}
              {image.is_refined && (
                <span className="px-1.5 py-0.5 bg-pink-500/80 text-white text-[10px] rounded flex items-center gap-0.5">
                  <Wand2 className="w-2.5 h-2.5" />
                  精修
                </span>
              )}
            </div>

            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

            <div className="absolute bottom-0 left-0 right-0 p-4 translate-y-full group-hover:translate-y-0 transition-transform">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  {isBest && (
                    <div className="flex items-center gap-1 text-yellow-400 text-xs font-semibold">
                      <Star className="w-3 h-3 fill-current" />
                      <span>最佳</span>
                    </div>
                  )}
                  {image.quality_score != null && (
                    <div className="text-xs text-slate-300">
                      质量分: {image.quality_score.toFixed(1)}
                    </div>
                  )}
                  <div className="text-xs text-slate-400">
                    种子: {image.seed}
                  </div>
                </div>

                <button
                  onClick={(e) => downloadImage(image, e)}
                  className="p-2 bg-blue-500/20 hover:bg-blue-500/30 rounded-lg transition-colors"
                >
                  <Download className="w-4 h-4 text-blue-300" />
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
