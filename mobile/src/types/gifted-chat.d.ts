import { IMessage } from 'react-native-gifted-chat';

declare module 'react-native-gifted-chat' {
  export interface GiftedChatProps {
    messages?: IMessage[];
    onSend?: (messages: IMessage[]) => void;
    user?: {
      _id: string | number;
      name?: string;
      avatar?: string;
    };
    isTyping?: boolean;
    renderSend?: (props: any) => React.ReactNode;
    renderInputToolbar?: (props: any) => React.ReactNode;
    renderComposer?: (props: any) => React.ReactNode;
    messagesContainerStyle?: any;
  }
}
