import { useState, useEffect, useContext } from "react";
import { Stack, TextField } from "@fluentui/react";
import { Button } from "@fluentui/react-components";

import styles from "./QuestionInput.module.css";
import { SpeechInput } from "./SpeechInput";
import { LoginContext } from "../../loginContext";
import { requireLogin } from "../../authConfig";

const SendIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className={styles.sendIcon}>
    <path d="M4 12h14" />
    <path d="m13 6 6 6-6 6" />
  </svg>
);

interface Props {
  onSend: (question: string) => void;
  disabled: boolean;
  initQuestion?: string;
  placeholder?: string;
  clearOnSend?: boolean;
  showSpeechInput?: boolean;
}

export const QuestionInput = ({
  onSend,
  disabled,
  placeholder,
  clearOnSend,
  initQuestion,
  showSpeechInput
}: Props) => {
  const [question, setQuestion] = useState<string>("");
  const { loggedIn } = useContext(LoginContext);
  const [isComposing, setIsComposing] = useState(false);

  useEffect(() => {
    if (initQuestion) setQuestion(initQuestion);
  }, [initQuestion]);

  const sendQuestion = () => {
    if (disabled || !question.trim()) return;

    onSend(question);

    if (clearOnSend) setQuestion("");
  };

  const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
    if (isComposing) return;

    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      sendQuestion();
    }
  };

  const onQuestionChange = (
    _ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string
  ) => {
    if (!newValue) setQuestion("");
    else if (newValue.length <= 1000) setQuestion(newValue);
  };

  const disableRequiredAccessControl = requireLogin && !loggedIn;
  const sendQuestionDisabled =
    disabled || !question.trim() || disableRequiredAccessControl;

  const effectivePlaceholder = disableRequiredAccessControl
    ? "Please login to continue..."
    : placeholder;

  return (
    <Stack horizontal className={styles.questionInputContainer}>
      <TextField
        className={styles.questionInputTextArea}
        disabled={disableRequiredAccessControl}
        placeholder={effectivePlaceholder}
        multiline
        resizable={false}
        borderless
        value={question}
        onChange={onQuestionChange}
        onKeyDown={onEnterPress}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
      />

      <div className={styles.questionInputButtonsContainer}>
        <Button
          size="large"
          icon={<SendIcon />}
          disabled={sendQuestionDisabled}
          onClick={sendQuestion}
          aria-label="Send"
        />
      </div>

      {showSpeechInput && <SpeechInput updateQuestion={setQuestion} />}
    </Stack>
  );
};