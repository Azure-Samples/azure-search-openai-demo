import { IconButton } from "@fluentui/react";

interface Props {
    isSpeaking?: boolean;
    onSpeechSynthesisClicked: () => void;
}

export const SpeechOutput = ({ isSpeaking, onSpeechSynthesisClicked }: Props) => {
    // The state of this is managed by the parent component, to ensure that
    // only one speech is outputted at any given time.
    return (
        <>
            {isSpeaking && (
                <IconButton
                    style={{ color: "red" }}
                    iconProps={{ iconName: "Volume3" }}
                    title="Speak answer"
                    ariaLabel="Speak answer"
                    onClick={() => onSpeechSynthesisClicked()}
                />
            )}
            {!isSpeaking && (
                <IconButton
                    style={{ color: "black" }}
                    iconProps={{ iconName: "Volume3" }}
                    title="Speak answer"
                    ariaLabel="Speak answer"
                    onClick={() => onSpeechSynthesisClicked()}
                />
            )}
        </>
    );
};
