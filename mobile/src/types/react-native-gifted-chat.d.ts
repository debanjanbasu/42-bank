import type React from 'react';

export interface IUser {
  _id: string | number;
  name?: string;
  avatar?: string;
}

export interface IMessage {
  _id: string | number;
  text: string;
  createdAt: Date | number;
  user: IUser;
  image?: string;
  video?: string;
  audio?: string;
  system?: boolean;
  sent?: boolean;
  received?: boolean;
  pending?: boolean;
}

export type GiftedChatProps<TMessage extends IMessage = IMessage> = {
  messages?: TMessage[];
  user?: IUser;
  onSend?: (messages: TMessage[]) => void;
  isTyping?: boolean;
  renderSend?: (props: unknown) => React.ReactNode;
  renderInputToolbar?: (props: unknown) => React.ReactNode;
  renderComposer?: (props: unknown) => React.ReactNode;
  messagesContainerStyle?: unknown;
  [key: string]: unknown;
};

export type GiftedChatType = React.ComponentType<GiftedChatProps> & {
  append: <TMessage extends IMessage>(
    currentMessages: TMessage[],
    messages: TMessage[] | TMessage,
    inverted?: boolean
  ) => TMessage[];
};

export const GiftedChat: GiftedChatType;
export const Send: React.ComponentType<Record<string, unknown>>;
export const InputToolbar: React.ComponentType<Record<string, unknown>>;
export const Composer: React.ComponentType<Record<string, unknown>>;
