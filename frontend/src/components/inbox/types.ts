import type { Message } from '../../types/message'

export interface QuestionItem extends Message {
  isReplied: boolean
  contactName: string
}
