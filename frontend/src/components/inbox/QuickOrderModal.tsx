import { useEffect, useState } from 'react'
import { orderApi } from '../../api/client'
import OrderForm from '../orders/OrderForm'
import type { Contact } from '../../types/contact'
import type { OrderCreate } from '../../types/order'

interface QuickOrderModalProps {
  open: boolean
  onClose: () => void
  messageId: number
  contactId: number
  contactName: string | null
  contacts: Contact[]
  onCreated: () => void
  onCreate: (data: OrderCreate) => Promise<void>
}

function QuickOrderModal({ open, onClose, messageId, contactId, contactName, contacts, onCreated, onCreate }: QuickOrderModalProps) {
  const [preview, setPreview] = useState<string | undefined>(undefined)
  const [amount, setAmount] = useState<number | null>(null)
  const [confidence, setConfidence] = useState<number>(0)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setPreview(undefined)
    setAmount(null)
    setConfidence(0)
    orderApi.suggest(messageId)
      .then((res) => {
        if (cancelled) return
        setPreview(res.message_preview || undefined)
        setAmount(res.suggested_amount)
        setConfidence(res.confidence)
      })
      .catch(() => {
        if (cancelled) return
        setPreview(undefined)
      })
    return () => { cancelled = true }
  }, [open, messageId])

  const previewText = preview && amount != null && confidence >= 0.6
    ? `${preview}\n\nВозможная сумма заказа: ${amount} ₽`
    : preview

  return (
    <OrderForm
      key={`${open ? 'open' : 'closed'}-${messageId}`}
      open={open}
      onClose={onClose}
      contacts={contacts}
      initial={{
        contact_id: contactId,
        contact_name: contactName,
        message_id: messageId,
        message_preview: previewText,
      }}
      onCreate={async (data) => {
        await onCreate(data)
        onCreated()
      }}
    />
  )
}

export default QuickOrderModal