import { useState, useEffect, useRef } from 'react'
import { MessageSquare, Globe, Shield, MessageCircle, CheckCircle, ArrowLeft, ArrowRight } from 'lucide-react'
import Button from '../components/common/Button'
import { settingsApi, type OnboardingData } from '../api/settings'
import { setStoredLogin, getStoredLogin, isConnectionError, markLocalOnboarded } from '../api/client'
import {
  TelegramStep,
  EmailStep,
  VkStep,
  ProxyStep,
  isValidLogin,
  type StepData,
} from './OnboardingSteps'

const STORAGE_KEY = 'bizibox_onboarding'

const defaultData: StepData = {
  login: '',
  telegram: { api_id: '', api_hash: '', phone: '', password_2fa: '', useCustomApi: false },
  email: { email: '', password: '', imap_host: '', smtp_host: '', imap_port: 993, smtp_port: 465 },
  vk: { group_id: '', password_2fa: '', token: '' },
  proxy: { mode: 'direct', type: 'socks5', host: '', port: '', username: '', password: '', secret: '' },
}

const MODE_LABELS: Record<string, string> = {
  direct: 'Напрямую (без VPN и прокси)',
  system_vpn: 'Системный VPN',
  custom_proxy: 'Свой прокси',
}

function loadProgress(): { step: number; data: StepData } {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      const d = parsed.data || {}
      return {
        step: parsed.step ?? 0,
        data: {
          ...defaultData,
          ...d,
          telegram: { ...defaultData.telegram, ...(d.telegram || {}) },
          email: { ...defaultData.email, ...(d.email || {}) },
          vk: { ...defaultData.vk, ...(d.vk || {}) },
          proxy: { ...defaultData.proxy, ...(d.proxy || {}) },
        },
      }
    }
  } catch {
    // ignore
  }
  return { step: 0, data: defaultData }
}

function saveProgress(step: number, data: StepData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data }))
}

function clearProgress() {
  localStorage.removeItem(STORAGE_KEY)
}

export default function Onboarding({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0)
  const [data, setData] = useState<StepData>(defaultData)
  const [saving, setSaving] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiExpanded, setApiExpanded] = useState(false)
  const prefilledLoginRef = useRef<string | null>(null)

  useEffect(() => {
    const saved = loadProgress()
    setStep(saved.step)
    setData(saved.data)
    if (saved.data.telegram.useCustomApi) {
      setApiExpanded(true)
    }
  }, [])

  useEffect(() => {
    const login = data.login.trim()
    if (!isValidLogin(login) || prefilledLoginRef.current === login) return
    const timer = setTimeout(() => {
      settingsApi
        .onboardingConfig(login)
        .then(config => {
          if (!config.telegram && !config.email && !config.vk && !config.proxy) return
          prefilledLoginRef.current = login
          const tg = config.telegram
          const em = config.email
          const vk = config.vk
          const px = config.proxy
          setData(prev => ({
            ...prev,
            telegram: {
              ...prev.telegram,
              phone: tg?.phone && !prev.telegram.phone ? tg.phone : prev.telegram.phone,
              password_2fa: tg?.password_2fa && !prev.telegram.password_2fa ? tg.password_2fa : prev.telegram.password_2fa,
            },
            email: {
              ...prev.email,
              email: em?.email && !prev.email.email ? em.email : prev.email.email,
              password: em?.password && !prev.email.password ? em.password : prev.email.password,
              imap_host: em?.imap_host && !prev.email.imap_host ? em.imap_host : prev.email.imap_host,
              imap_port: em?.imap_port != null && !prev.email.imap_host ? em.imap_port : prev.email.imap_port,
              smtp_host: em?.smtp_host && !prev.email.smtp_host ? em.smtp_host : prev.email.smtp_host,
              smtp_port: em?.smtp_port != null && !prev.email.smtp_host ? em.smtp_port : prev.email.smtp_port,
            },
            vk: {
              ...prev.vk,
              group_id: vk?.group_id && !prev.vk.group_id ? String(vk.group_id) : prev.vk.group_id,
              password_2fa: vk?.password_2fa && !prev.vk.password_2fa ? vk.password_2fa : prev.vk.password_2fa,
              token: vk?.token && !prev.vk.token ? vk.token : prev.vk.token,
            },
            proxy: {
              ...prev.proxy,
              type: px?.type && !prev.proxy.host ? (px.type || prev.proxy.type) : prev.proxy.type,
              host: px?.host && !prev.proxy.host ? px.host : prev.proxy.host,
              port: px?.port != null && !prev.proxy.host ? String(px.port) : prev.proxy.port,
              mode: px?.host ? 'custom_proxy' : prev.proxy.mode,
            },
          }))
        })
        .catch(() => {})
    }, 400)
    return () => clearTimeout(timer)
  }, [data.login])

  const updateData = (section: keyof StepData, field: string, value: string | number | boolean) => {
    if (section === 'login') {
      setData(prev => ({ ...prev, login: value as string }))
      return
    }
    setData(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value },
    }))
  }

  const handleNext = () => {
    saveProgress(step + 1, data)
    setStep(s => s + 1)
  }

  const handleBack = () => {
    setStep(s => s - 1)
  }

  const handleFinish = async () => {
    if (!isValidLogin(data.login)) {
      setError('Введите логин длиной от 1 до 100 символов')
      return
    }
    setSaving(true)
    setError(null)
    const login = data.login.trim()
    const prevLogin = getStoredLogin()
    try {
      const payload: OnboardingData = { login }
      const tg = data.telegram
      if (tg.phone) {
        payload.telegram = {
          api_id: tg.api_id ? Number(tg.api_id) : undefined,
          api_hash: tg.api_hash || undefined,
          phone: tg.phone || undefined,
          password_2fa: tg.password_2fa || undefined,
        }
      }
      if (data.email.email) {
        payload.email = {
          email: data.email.email,
          password: data.email.password,
          imap_host: data.email.imap_host || undefined,
          imap_port: data.email.imap_port,
          smtp_host: data.email.smtp_host || undefined,
          smtp_port: data.email.smtp_port,
        }
      }
      if (data.vk.group_id || data.vk.token) {
        payload.vk = {
          group_id: data.vk.group_id ? Number(data.vk.group_id) : undefined,
          password_2fa: data.vk.password_2fa || undefined,
          token: data.vk.token || undefined,
        }
      }
      payload.proxy = {
        mode: data.proxy.mode,
        enabled: data.proxy.mode === 'custom_proxy',
        type: data.proxy.type,
        host: data.proxy.host || undefined,
        port: data.proxy.port ? Number(data.proxy.port) : undefined,
        username: data.proxy.username || undefined,
        password: data.proxy.password || undefined,
        secret: data.proxy.secret || undefined,
      }
      const result = await settingsApi.onboardingComplete(payload)
      if (result.login) {
        setStoredLogin(result.login)
      }
      markLocalOnboarded()
      clearProgress()
      // Сброс офлайн-кэша react-query только при смене логина:
      // если логин тот же — оставляем кэш, чтобы видеть уже скачанные сообщения.
      if (prevLogin && prevLogin !== login) {
        localStorage.removeItem('BIZIBOX_RQ_CACHE')
      }
      onComplete()
    } catch (err) {
      if (isConnectionError(err)) {
        // Сервер реально недоступен — завершаем онбординг локально:
        // данные ушли в offline-очередь и синхронизируются при восстановлении связи.
        setStoredLogin(login)
        markLocalOnboarded()
        clearProgress()
        onComplete()
      } else {
        setError(err instanceof Error ? err.message : 'Ошибка сохранения')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDemo = async () => {
    if (demoLoading) return
    setDemoLoading(true)
    setError(null)
    try {
      const result = await settingsApi.demo()
      if (result.login) {
        setStoredLogin(result.login)
      }
      markLocalOnboarded()
      clearProgress()
      localStorage.removeItem('BIZIBOX_RQ_CACHE')
      onComplete()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки демо')
      setDemoLoading(false)
    }
  }

  const steps = [
    { icon: MessageSquare, label: 'Telegram', color: 'bg-blue-500' },
    { icon: Globe, label: 'Email', color: 'bg-green-500' },
    { icon: MessageCircle, label: 'ВКонтакте', color: 'bg-blue-600' },
    { icon: Shield, label: 'Прокси', color: 'bg-purple-500' },
    { icon: CheckCircle, label: 'Готово', color: 'bg-emerald-500' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="flex items-center justify-center gap-2 mb-8">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${
                i <= step ? s.color : 'bg-gray-300'
              }`}>
                {i < step ? '✓' : i + 1}
              </div>
              <span className={`text-xs ${i <= step ? 'text-gray-700 font-medium' : 'text-gray-400'}`}>
                {s.label}
              </span>
              {i < steps.length - 1 && <div className={`w-8 h-0.5 ${i < step ? 'bg-blue-500' : 'bg-gray-300'}`} />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          {step === 0 && (
            <TelegramStep
              data={data}
              updateData={updateData}
              expanded={apiExpanded}
              setExpanded={setApiExpanded}
            />
          )}

          {step === 1 && <EmailStep data={data} updateData={updateData} />}

          {step === 2 && <VkStep data={data} updateData={updateData} />}

          {step === 3 && <ProxyStep data={data} updateData={updateData} />}

          {step === 4 && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-emerald-100 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-emerald-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Настройка завершена</h2>
                  <p className="text-sm text-gray-500">Проверьте введённые данные</p>
                </div>
              </div>
              <div className="bg-gray-50 rounded-xl p-4 space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Логин:</span>
                  <span className="text-right font-medium">{data.login.trim() || '—'}</span>
                </div>
                {data.telegram.phone && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Telegram:</span>
                    <span className="text-right">{data.telegram.phone} {data.telegram.useCustomApi ? '(API: пользовательский)' : '(API: серверный)'}</span>
                  </div>
                )}
                {data.email.email && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Email:</span>
                    <span>{data.email.email}</span>
                  </div>
                )}
                {data.vk.group_id && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">ВКонтакте:</span>
                    <span className="text-right">{data.vk.group_id}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Сеть (Telegram):</span>
                  <span className="text-right">{MODE_LABELS[data.proxy.mode] ?? data.proxy.mode}</span>
                </div>
                {data.proxy.mode === 'custom_proxy' && data.proxy.host && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Прокси:</span>
                    <span className="text-right">{data.proxy.type}://{data.proxy.host}:{data.proxy.port}</span>
                  </div>
                )}
                {!data.telegram.phone && !data.email.email && !data.vk.group_id && data.proxy.mode === 'direct' && (
                  <p className="text-gray-400 text-center">Не введено ни одного параметра</p>
                )}
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>
          )}

          <div className="flex justify-between mt-8 pt-6 border-t border-gray-100">
            <div>
              {step > 0 ? (
                <Button variant="ghost" onClick={handleBack}>
                  <ArrowLeft className="w-4 h-4 mr-1" /> Назад
                </Button>
              ) : (
                <div />
              )}
            </div>
            <div className="flex gap-2">
              {step < 4 && (
                <Button onClick={handleNext} disabled={step === 0 && !isValidLogin(data.login)}>
                  Далее <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              )}
              {step === 4 && (
                <Button onClick={handleFinish} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Завершить настройку'}
                </Button>
              )}
            </div>
          </div>

          {step === 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100 text-center">
              <p className="text-sm text-gray-500 mb-2">Не хотите настраивать сейчас?</p>
              <Button variant="ghost" onClick={handleDemo} disabled={demoLoading} className="w-full">
                {demoLoading ? 'Загрузка демо...' : 'Попробовать демо с примерами данных'}
              </Button>
              {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
