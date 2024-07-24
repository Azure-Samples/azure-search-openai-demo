import { useState } from "react";
import { IconButton } from "@fluentui/react";
import { useTranslation } from "react-i18next";
import { supportedLngs } from "../../i18n/config";

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

const getUtterance = function (text: string, lngCode: string = "en-US") {
    if (synth) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = lngCode;
        utterance.volume = 1;
        utterance.rate = 1;
        utterance.pitch = 1;

        let voice = synth.getVoices().filter((voice: SpeechSynthesisVoice) => voice.lang === lngCode)[0];
        if (!voice) {
            voice = synth.getVoices().filter((voice: SpeechSynthesisVoice) => voice.lang === "en-US")[0];
        }

        utterance.voice = voice;
        return utterance;
    }
};

export const SpeechOutputBrowser = ({ answer }: Props) => {
    const { t, i18n } = useTranslation();
    const currentLng = i18n.language;
    let lngCode = supportedLngs[currentLng]?.locale;
    if (!lngCode) {
        lngCode = "en-US";
    }
    const [isPlaying, setIsPlaying] = useState<boolean>(false);

    const startOrStopSpeech = (answer: string) => {
        if (synth != null) {
            if (isPlaying) {
                synth.cancel(); // removes all utterances from the utterance queue.
                setIsPlaying(false);
                return;
            }
            const utterance: SpeechSynthesisUtterance | undefined = getUtterance(answer, lngCode);

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
            title={t("tooltips.speakAnswer")}
            ariaLabel={t("tooltips.speakAnswer")}
            onClick={() => startOrStopSpeech(answer)}
            disabled={!synth}
        />
    );
};
