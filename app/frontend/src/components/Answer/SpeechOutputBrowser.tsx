import { useState } from "react";
import { IconButton } from "@fluentui/react";

interface Props {
    answer: string;
}

const SpeechSynthesis = (window as any).speechSynthesis || (window as any).webkitSpeechSynthesis;

let synth: SpeechSynthesis | null = null;

try {
    synth = SpeechSynthesis;
} catch (err) {
    console.error("SpeechSynthesis is not supported");
}

export const SpeechOutputBrowser = ({ answer }: Props) => {
    const [isSpeaking, SetIsSpeaking] = useState<boolean>(false);

    const utterance = new SpeechSynthesisUtterance(answer);
    const onSpeechSynthesisClicked = (utterance: SpeechSynthesisUtterance) => {
        if (synth != null) {
            utterance.lang = "en-US";
            utterance.volume = 1;
            utterance.rate = 1;
            utterance.pitch = 1;
            utterance.voice = synth.getVoices().filter((voice: SpeechSynthesisVoice) => voice.lang === "en-US")[0];
            console.log(utterance.voice);

            synth.speak(utterance);

            utterance.onstart = () => {
                SetIsSpeaking(true);
            };
            utterance.onend = () => {
                SetIsSpeaking(false);
            };
        }
    };
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
                    onClick={() => onSpeechSynthesisClicked(utterance)}
                />
            )}
            {!isSpeaking && (
                <IconButton
                    style={{ color: "black" }}
                    iconProps={{ iconName: "Volume3" }}
                    title="Speak answer"
                    ariaLabel="Speak answer"
                    onClick={() => onSpeechSynthesisClicked(utterance)}
                />
            )}
        </>
    );
};
