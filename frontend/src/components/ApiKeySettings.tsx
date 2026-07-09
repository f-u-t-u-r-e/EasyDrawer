import React, { useState } from 'react'
import { Key, Save, X, Eye, EyeOff, Globe } from 'lucide-react'
import { setApiKey, setLLMConfig, getLLMConfig } from '@/services/api'

interface ApiKeySettingsProps {
  onClose: () => void
}

interface LLMConfig {
  provider: string
  apiKey: string
  baseUrl: string
  model: string
}

const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic Claude', defaultUrl: 'https://api.anthropic.com', models: ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5'] },
  { value: 'openai', label: 'OpenAI', defaultUrl: 'https://api.openai.com/v1', models: ['gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo'] },
  { value: 'deepseek', label: 'DeepSeek', defaultUrl: 'https://api.deepseek.com', models: ['deepseek-chat', 'deepseek-coder'] },
  { value: 'moonshot', label: 'Moonshot AI (Kimi)', defaultUrl: 'https://api.moonshot.cn/v1', models: ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'] },
  { value: 'zhipu', label: '智谱 AI (GLM)', defaultUrl: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4', 'glm-4-plus', 'glm-3-turbo'] },
  { value: 'custom', label: '自定义 / OpenAI 兼容', defaultUrl: '', models: [] },
]

export const ApiKeySettings: React.FC<ApiKeySettingsProps> = ({ onClose }) => {
  const savedConfig = getLLMConfig()
  const [config, setConfig] = useState<LLMConfig>(savedConfig || {
    provider: 'anthropic',
    apiKey: '',
    baseUrl: 'https://api.anthropic.com',
    model: 'claude-sonnet-4-6',
  })
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)

  const selectedProvider = PROVIDERS.find(p => p.value === config.provider)

  const handleProviderChange = (provider: string) => {
    const providerData = PROVIDERS.find(p => p.value === provider)
    setConfig({
      ...config,
      provider,
      baseUrl: providerData?.defaultUrl || '',
      model: providerData?.models[0] || '',
    })
  }

  const handleSave = () => {
    setLLMConfig(config)
    setApiKey(config.apiKey || null)
    setSaved(true)
    setTimeout(() => {
      onClose()
    }, 1000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(8px)' }} onClick={onClose}>
      <div className="card max-w-2xl w-full relative max-h-[90vh] overflow-y-auto animate-scale-in" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div
            className="p-2.5 rounded-xl"
            style={{ background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.2)' }}
          >
            <Key className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">LLM 配置</h2>
            <p className="text-xs text-slate-500">配置大语言模型提供商和 API 密钥</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* 提供商选择 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <Globe className="w-4 h-4 inline mr-1" />
              提供商
            </label>
            <select
              value={config.provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="select-field"
            >
              {PROVIDERS.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* API Base URL */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              API 地址
            </label>
            <input
              type="text"
              value={config.baseUrl}
              onChange={(e) => setConfig({ ...config, baseUrl: e.target.value })}
              placeholder="https://api.example.com"
              className="input-field font-mono text-sm"
            />
            <p className="text-xs text-slate-500 mt-1">
              支持 OpenAI 兼容接口（如代理、中转服务）
            </p>
          </div>

          {/* 模型选择 */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              模型
            </label>
            {selectedProvider && selectedProvider.models.length > 0 ? (
              <select
                value={config.model}
                onChange={(e) => setConfig({ ...config, model: e.target.value })}
                className="select-field"
              >
                {selectedProvider.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={config.model}
                onChange={(e) => setConfig({ ...config, model: e.target.value })}
                placeholder="gpt-4o"
                className="input-field font-mono text-sm"
              />
            )}
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              API Key
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={config.apiKey}
                onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                placeholder={
                  config.provider === 'anthropic' ? 'sk-ant-api03-...' :
                  config.provider === 'openai' ? 'sk-...' :
                  config.provider === 'deepseek' ? 'sk-...' :
                  'your-api-key'
                }
                className="input-field pr-10 font-mono text-sm"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              密钥仅在浏览器中保存，不会上传到服务器存储
            </p>
          </div>

          {/* 提示信息 */}
          <div className="rounded-lg p-3" style={{ background: 'rgba(245, 158, 11, 0.06)', border: '1px solid rgba(245, 158, 11, 0.12)' }}>
            <p className="text-xs text-amber-300/80">
              💡 <strong>获取 API 密钥：</strong>
              <br />
              {config.provider === 'anthropic' && (
                <>
                  访问{' '}
                  <a
                    href="https://console.anthropic.com/settings/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-blue-200"
                  >
                    Anthropic Console
                  </a>
                </>
              )}
              {config.provider === 'openai' && (
                <>
                  访问{' '}
                  <a
                    href="https://platform.openai.com/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-blue-200"
                  >
                    OpenAI Platform
                  </a>
                </>
              )}
              {config.provider === 'deepseek' && (
                <>
                  访问{' '}
                  <a
                    href="https://platform.deepseek.com/api_keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-blue-200"
                  >
                    DeepSeek Platform
                  </a>
                </>
              )}
              {config.provider === 'moonshot' && (
                <>
                  访问{' '}
                  <a
                    href="https://platform.moonshot.cn/console/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-blue-200"
                  >
                    Moonshot 控制台
                  </a>
                </>
              )}
              {config.provider === 'zhipu' && (
                <>
                  访问{' '}
                  <a
                    href="https://open.bigmodel.cn/usercenter/apikeys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-blue-200"
                  >
                    智谱开放平台
                  </a>
                </>
              )}
              {config.provider === 'custom' && '配置您的自定义 API 地址和密钥'}
            </p>
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={handleSave} className="btn-primary flex-1 flex items-center justify-center gap-2">
              <Save className="w-4 h-4" />
              {saved ? '已保存 ✓' : '保存配置'}
            </button>
            <button
              onClick={onClose}
              className="px-6 py-3.5 rounded-xl text-slate-300 hover:text-slate-100 transition-all text-sm"
              style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)' }}
            >
              取消
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
