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

const getUtterance = function (text: string) {
    if (synth) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "en-US";
        utterance.volume = 1;
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.voice = synth.getVoices().filter((voice: SpeechSynthesisVoice) => voice.lang === "en-US")[0];
        return utterance;
    }
};

export const SpeechOutputBrowser = ({ answer }: Props) => {
    const [isPlaying, setIsPlaying] = useState<boolean>(false);

    const startOrStopSpeech = (answer: string) => {
        if (synth != null) {
            if (isPlaying) {
                synth.cancel(); // removes all utterances from the utterance queue.
                setIsPlaying(false);
                return;
            }
            const utterance: SpeechSynthesisUtterance | undefined = getUtterance(answer);

            if (!utterance) {
                return;
            }

            synth.speak(utterance);

            utterance.onstart = () => {
                setIsPlaying(true);
                return;
            };

            utterance.onend = () => {
                setIsPlaying(false);
                return;
            };
        }
    };
    const color = isPlaying ? "red" : "black";

    return (
        <IconButton
            style={{ color: color }}
            iconProps={{ iconName: "Volume3" }}
            title="Speak answer"
            ariaLabel="Speak answer"
            onClick={() => startOrStopSpeech(answer)}
            disabled={!synth}
        />
    );
};
