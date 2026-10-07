import { useState, useEffect, useCallback, useRef } from 'react'
import { MessageSquare, Send, CheckCircle, Smartphone, Clock, Lock } from 'lucide-react'
import Button from '../common/Button'
import { ApiError, channelApi } from '../../api/client'
import { settingsApi } from '../../api/settings'

const MIN_COOLDOWN = 60

interface TelegramConnectProps {
  onConnected: () => void
}

function TelegramConnect({ onConnected }: TelegramConnectProps) {
  const [phone, setPhone] = useState('')

  useEffect(() => {
    settingsApi.onboardingConfig().then(config => {
      if (config.telegram?.phone) setPhone(config.telegram.phone)
    }).catch(() => {})
  }, [])
  const [code, setCode] = useState('')
  const [channelId, setChannelId] = useState<number | null>(null)
  const [phoneCodeHash, setPhoneCodeHash] = useState<string | null>(null)
  const [codeType, setCodeType] = useState<'app' | 'sms' | 'call'>('app')
  const [nextType, setNextType] = useState<'sms' | 'call' | 'flashcall' | 'missed_call' | undefined>(undefined)
  const [password, setPassword] = useState('')
  const [step, setStep] = useState<'phone' | 'code' | 'password'>('phone')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showResend, setShowResend] = useState(false)
  const [timer, setTimer] = useState(0)
  const [waitTimer, setWaitTimer] = useState(0)
  const [isFloodWait, setIsFloodWait] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  useEffect(() => {
    return clearTimer
  }, [clearTimer])

  const startFloodWait = useCallback((seconds: number) => {
    setIsFloodWait(true)
    setWaitTimer(seconds)
    clearTimer()
    timerRef.current = setInterval(() => {
      setWaitTimer((t) => {
        if (t <= 1) {
          clearTimer()
          setIsFloodWait(false)
          setError(null)
          return 0
        }
        return t - 1
      })
    }, 1000)
  }, [clearTimer])

  const extractFloodSeconds = (err: unknown): number | null => {
    if (err instanceof ApiError && err.status === 429) {
      const match = err.message.match(/(\d+)\s*секунд/)
      if (match) return parseInt(match[1], 10)
    }
    return null
  }

  const describeError = (err: unknown, fallback: string): string => {
    if (err instanceof DOMException && err.name === 'AbortError') {
      return 'Сервер не ответил вовремя. Код мог быть отправлен — проверьте Telegram/SMS, затем введите его или повторите запрос'
    }
    if (err instanceof TypeError) {
      return 'Нет соединения с сервером. Проверьте интернет и попробуйте снова'
    }
    return err instanceof Error ? err.message : fallback
  }

  const resendLabel = (type: 'sms' | 'call' | 'flashcall' | 'missed_call') => {
    switch (type) {
      case 'sms': return 'SMS'
      case 'call': return 'звонок'
      case 'flashcall': return 'флеш-звонок'
      case 'missed_call': return 'пропущенный звонок'
      default: return type
    }
  }

  const startResendTimer = useCallback((delay?: number, serverTimeout?: number) => {
    setShowResend(false)
    const seconds = serverTimeout || delay || MIN_COOLDOWN
    setTimer(Math.round(seconds))
    clearTimer()
    timerRef.current = setInterval(() => {
      setTimer((t) => {
        if (t <= 1) {
          clearTimer()
          setShowResend(true)
          return 0
        }
        return t - 1
      })
    }, 1000)
  }, [clearTimer])

  const sendCode = async (via: 'app') => {
    setLoading(true)
    setError(null)
    try {
      const res = await channelApi.connectTelegram({ phone, via })
      if (res.channel_id) {
        setChannelId(res.channel_id)
      }
      if (res.phone_code_hash) {
        setPhoneCodeHash(res.phone_code_hash)
      }
      if (res.code_type) {
        setCodeType(res.code_type)
      }
      setNextType(res.next_type)
      setStep('code')
      startResendTimer(undefined, res.timeout)
    } catch (err) {
      const sec = extractFloodSeconds(err)
      if (sec) {
        startFloodWait(sec)
      } else {
        setError(describeError(err, 'Ошибка отправки кода'))
      }
    } finally {
      setLoading(false)
    }
  }

  const resendSms = async () => {
    if (!channelId || !phoneCodeHash) return
    setResending(true)
    setError(null)
    try {
      const res = await channelApi.resendTelegram({
        channel_id: channelId,
        phone_code_hash: phoneCodeHash,
      })
      if (res.phone_code_hash) {
        setPhoneCodeHash(res.phone_code_hash)
      }
      if (res.code_type) {
        setCodeType(res.code_type)
      }
      setNextType(res.next_type)
      startResendTimer(undefined, res.timeout)
    } catch (err) {
      const sec = extractFloodSeconds(err)
      if (sec) {
        startFloodWait(sec)
      } else {
        setError(describeError(err, 'Ошибка повторной отправки'))
      }
    } finally {
      setResending(false)
    }
  }

  const confirmCode = async () => {
    if (!channelId || !phoneCodeHash) return
    setLoading(true)
    setError(null)
    try {
      const res = await channelApi.confirmTelegram({
        channel_id: channelId,
        code,
        phone_code_hash: phoneCodeHash,
      })
      if (res.status === 'code_expired' && res.phone_code_hash) {
        setPhoneCodeHash(res.phone_code_hash)
        setCode('')
        setError(res.message || 'Код истёк. Новый код отправлен')
        startResendTimer()
      } else if (res.status === 'password_needed') {
        setStep('password')
        setError(null)
      } else {
        clearTimer()
        onConnected()
      }
    } catch (err) {
      const sec = extractFloodSeconds(err)
      if (sec) {
        startFloodWait(sec)
      } else {
        setError(describeError(err, 'Ошибка подтверждения'))
      }
    } finally {
      setLoading(false)
    }
  }

  const submitPassword = async () => {
    if (!channelId) return
    setLoading(true)
    setError(null)
    try {
      await channelApi.submitPassword({ channel_id: channelId, password })
      clearTimer()
      onConnected()
    } catch (err) {
      const sec = extractFloodSeconds(err)
      if (sec) {
        startFloodWait(sec)
      } else {
        setError(describeError(err, 'Неверный пароль'))
      }
    } finally {
      setLoading(false)
    }
  }

  const anyDisabled = loading || resending || isFloodWait

  if (step === 'password') {
    return (
      <div className="p-4 rounded-xl border border-yellow-200 bg-yellow-50 space-y-3">
        <div className="flex items-center gap-2 text-yellow-700">
          <Lock className="w-5 h-5" />
          <span className="font-medium">Требуется облачный пароль (2FA)</span>
        </div>
        <p className="text-sm text-yellow-600">Введите пароль от Telegram:</p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Пароль"
          className="w-full px-3 py-2 rounded-lg border border-yellow-300 bg-white text-sm outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500"
          onKeyDown={(e) => { if (e.key === 'Enter') submitPassword() }}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button onClick={submitPassword} disabled={anyDisabled || !password}>
          {loading ? 'Подключение...' : 'Подтвердить пароль'}
        </Button>
      </div>
    )
  }

  if (step === 'code') {
    return (
      <div className="p-4 rounded-xl border border-blue-200 bg-blue-50 space-y-3">
        <div className="flex items-center gap-2 text-blue-700">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">
            {codeType === 'sms'
              ? 'Код отправлен по SMS'
              : codeType === 'call'
                ? 'Код отправлен по звонку'
                : 'Код отправлен в Telegram'}
          </span>
        </div>
        {codeType === 'app' && (
          <p className="text-xs text-blue-500">
            Проверьте чат «Служебные уведомления» в Telegram. Новый запрос отменяет предыдущий код — дождитесь повторной отправки.
          </p>
        )}
        {codeType !== 'app' && (
          <p className="text-xs text-blue-500">Введите код, пришедший на телефон.</p>
        )}
        <p className="text-sm text-blue-600">Введите код:</p>
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="12345"
          className="w-full px-3 py-2 rounded-lg border border-blue-300 bg-white text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          maxLength={10}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button onClick={confirmCode} disabled={anyDisabled || !code}>
          {loading ? 'Подтверждение...' : 'Подтвердить'}
        </Button>
        <div className="flex items-center gap-2 pt-1">
          {isFloodWait ? (
            <div className="flex items-center gap-1 text-sm text-orange-600">
              <Clock className="w-4 h-4" />
              <span>Подождите {waitTimer} с</span>
            </div>
          ) : (
            <>
              <Smartphone className="w-4 h-4 text-gray-400" />
              {showResend ? (
                <>
                  <button
                    onClick={resendSms}
                    disabled={anyDisabled}
                    className="text-sm text-blue-600 hover:text-blue-800 underline underline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {resending ? 'Отправка...' : nextType ? `Отправить повторно (${resendLabel(nextType)})` : 'Отправить код повторно'}
                  </button>
                  {codeType !== 'app' && (
                    <button
                      onClick={() => sendCode('app')}
                      disabled={anyDisabled}
                      className="text-sm text-gray-500 hover:text-gray-700 underline underline-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Получить код в Telegram
                    </button>
                  )}
                </>
              ) : timer > 0 ? (
                <span className="text-sm text-gray-500">
                  Повторная отправка через {timer} с
                </span>
              ) : null}
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 rounded-xl border border-gray-200 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-blue-600" />
        <span className="font-medium text-gray-900">Подключить Telegram</span>
      </div>
      {isFloodWait && (
        <div className="flex items-center gap-1 text-sm text-orange-600 bg-orange-50 p-2 rounded-lg">
          <Clock className="w-4 h-4" />
          <span>Слишком много запросов. Подождите {waitTimer} с</span>
        </div>
      )}
      <input
        type="tel"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        placeholder="+79991234567"
        className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="text-xs text-gray-500">
        Код придёт в чат «Служебные уведомления» в Telegram. Новый запрос отменяет предыдущий код — не нажимайте кнопку повторно.
      </p>
      <div className="flex flex-col gap-2">
        <Button onClick={() => sendCode('app')} disabled={anyDisabled || !phone}>
          {loading ? <Send className="w-4 h-4 animate-pulse" /> : null}
          {loading ? 'Отправка...' : 'Получить код в Telegram'}
        </Button>
      </div>
    </div>
  )
}

export default TelegramConnect