import React, { useState, useCallback, useEffect } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { GiftedChat, IMessage, Send, InputToolbar, Composer } from 'react-native-gifted-chat';
import { IconButton, ActivityIndicator } from 'react-native-paper';
import { useAuth } from '@/contexts/AuthContext';
import { useA2A } from '@/hooks/useA2A';
import { darkTheme } from '@/utils/theme';

type GiftedChatProps = React.ComponentProps<typeof GiftedChat>;

export default function ChatScreen() {
const { user } = useAuth();
const { sendMessage: sendA2AMessage } = useA2A();
const [messages, setMessages] = useState<IMessage[]>([]);
const [isStreaming, setIsStreaming] = useState(false);

  // Match "send $50 to bob" or "transfer 100 to alice for lunch"
  const extractTransferIntent = (text: string) => {
    const match = text.match(
      /(?:send|transfer)\s+\$?(\d+(?:\.\d+)?)\s+to\s+(\w+)(?:\s+(?:for\s+)?(.+))?/i,
    );
    if (!match) return null;
    return { amount: parseFloat(match[1]), recipient: match[2], note: match[3] ?? 'Transfer' };
  };

  useEffect(() => {
    setMessages([
      {
        _id: 'welcome',
        text: `Hello, ${user?.username || 'there'}! 👋\n\nI'm your 42-Bank AI assistant. I can help you with:\n\n• Checking your balance\n• Sending money to friends\n• Viewing transaction history\n• Opening new accounts\n\nWhat would you like to do today?`,
        createdAt: new Date(),
        user: {
          _id: 'agent',
          name: '42-Bank AI',
        },
      },
    ]);
  }, [user?.username]);

const onSend = useCallback(
async (newMessages: IMessage[] = []) => {
const message = newMessages[0];
setMessages((previousMessages) =>
GiftedChat.append(previousMessages, newMessages)
);

// Send message directly to A2A agent
// Backend handles transaction execution via session-based auth
setIsStreaming(true);
try {
let fullResponse = '';
await sendA2AMessage(message.text, (chunk: string, done: boolean) => {
fullResponse += chunk;
if (done) {
const agentMessage: IMessage = {
_id: Date.now().toString(),
text: fullResponse,
createdAt: new Date(),
user: {
_id: 'agent',
name: '42-Bank AI',
},
};
setMessages((previousMessages) =>
GiftedChat.append(previousMessages, [agentMessage])
);
setIsStreaming(false);
}
});
} catch (error) {
const errorMessage: IMessage = {
_id: Date.now().toString(),
text: '❌ Sorry, I encountered an error. Please try again.',
createdAt: new Date(),
user: {
_id: 'system',
name: 'System',
},
};
setMessages((previousMessages) =>
GiftedChat.append(previousMessages, [errorMessage])
);
setIsStreaming(false);
}
},
[sendA2AMessage],
);

  const renderSend = (props: any) => (
    <Send {...props} containerStyle={styles.sendContainer} disabled={isStreaming}>
      {isStreaming ? (
        <ActivityIndicator size="small" color={darkTheme.colors.primary} />
      ) : (
        <IconButton icon="send" iconColor={darkTheme.colors.primary} size={24} />
      )}
    </Send>
  );

  const renderInputToolbar = (props: any) => (
    <InputToolbar
      {...props}
      containerStyle={styles.inputToolbar}
      primaryStyle={styles.inputPrimary}
    />
  );

  const renderComposer = (props: any) => (
    <Composer
      {...props}
      textInputStyle={styles.composer}
      placeholder="Ask about your account..."
      placeholderTextColor={darkTheme.colors.textSecondary}
    />
  );

return (
<View style={styles.container}>
<GiftedChat
messages={messages}
onSend={onSend}
user={{
_id: user?.user_id || 'anonymous',
name: user?.username || 'User',
}}
isTyping={isStreaming}
renderSend={renderSend}
renderInputToolbar={renderInputToolbar}
renderComposer={renderComposer}
messagesContainerStyle={styles.messagesContainer}
/>
{Platform.OS === 'android' && <KeyboardAvoidingView behavior="padding" />}
</View>
);
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: darkTheme.colors.background,
  },
  messagesContainer: {
    backgroundColor: darkTheme.colors.background,
  },
  sendContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
    marginBottom: 5,
  },
  inputToolbar: {
    backgroundColor: darkTheme.colors.surface,
    borderTopWidth: 0,
    borderRadius: 25,
    marginHorizontal: 10,
    marginBottom: 5,
  },
  inputPrimary: {
    alignItems: 'center',
  },
  composer: {
    color: darkTheme.colors.text,
    backgroundColor: 'transparent',
    paddingTop: 10,
    paddingHorizontal: 15,
  },
});
