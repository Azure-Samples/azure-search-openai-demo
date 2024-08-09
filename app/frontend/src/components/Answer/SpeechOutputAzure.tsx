import { useState } from "react";

import { IconButton } from "@fluentui/react";
import { getSpeechApi } from "../../api";

interface Props {
    answer: string;
    urls: (string | null)[];
    updateSpeechUrls: (urls: (string | null)[]) => void;
    index: number;
}

let audio = new Audio();

export const SpeechOutputAzure = ({ answer, urls, updateSpeechUrls, index }: Props) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const playAudio = async (url: string) => {
        audio = new Audio(url);
        await audio.play();
        audio.addEventListener("ended", () => {
            setIsPlaying(false);
        });
        setIsPlaying(true);
    };

    const startOrStopSpeech = async (answer: string) => {
        if (isPlaying) {
            audio.pause();
            setIsPlaying(false);
            return;
        }
        if (urls[index]) {
            playAudio(urls[index]);
            return;
        }
        setIsLoading(true);
        await getSpeechApi(answer).then(async speechUrl => {
            if (!speechUrl) {
                alert("Speech output is not available.");
                console.error("Speech output is not available.");
                return;
            }
            setIsLoading(false);
            updateSpeechUrls(urls.map((url, i) => (i === index ? speechUrl : url)));
            playAudio(speechUrl);
        });
    };

    const color = isPlaying ? "red" : "black";
    return isLoading ? (
        <IconButton style={{ color: color }} iconProps={{ iconName: "Sync" }} title="Loading" ariaLabel="Loading answer" disabled={true} />
    ) : (
        <IconButton
            style={{ color: color }}
            iconProps={{ iconName: "Volume3" }}
            title="Speak answer"
            ariaLabel="Speak answer"
            onClick={() => startOrStopSpeech(answer)}
        />
    );
};
